from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DBSession
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.database import get_db
from app.db.models import Session as ChatSession, Message
from app.schemas.chat import LegalQuery, ChatApiResponse, ChatResponse
from app.services.gemini import generate_json, CHAT_SYSTEM_PROMPT, GeminiError
import json
import re
from pathlib import Path
from functools import lru_cache
from app.routers.laws import _load_sections, _load_cases


@lru_cache(maxsize=1)
def _load_scenarios() -> dict:
    path = Path(__file__).resolve().parent.parent / "data" / "scenarios.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

router = APIRouter(prefix="/api/legal", tags=["chat"])
log = get_logger(__name__)


RECENT_QUERY_RE = re.compile(r"\b(today|recent|latest|new|inniku|aaju|aaj|recent ah|recent la|latest ah|latest la|sami patha)\b", re.IGNORECASE)


def _wants_recent_news(query: str) -> bool:
    """Detect queries like 'today case enna', 'recent SC judgment', 'latest news'."""
    if not RECENT_QUERY_RE.search(query):
        return False
    legal_terms = ["case", "judgment", "ruling", "verdict", "news", "law", "court", "ipc", "bns",
                   "வழக்கு", "தீர்ப்பு", "மुक़दमा", "फ़ैसला"]
    q_low = query.lower()
    return any(term in q_low for term in legal_terms)


def _ground_with_laws(query: str, max_sections: int = 8, max_cases: int = 4, max_scenarios: int = 3) -> str:
    """Pull the most relevant IPC/BNS sections + landmark cases + real-life scenarios from our DB."""
    q = query.lower()
    sections_data = _load_sections()
    cases_data = _load_cases()
    scenarios_data = _load_scenarios()

    def section_score(s):
        score = 0
        hay = " ".join([
            s.get("title", ""), s.get("category", ""),
            " ".join(s.get("keywords", [])),
        ]).lower()
        for word in q.split():
            if len(word) > 3 and word in hay:
                score += 2
        # Direct section number boost
        if s.get("ipc") and s["ipc"].lower() in q:
            score += 10
        if s.get("bns") and s["bns"].lower() in q:
            score += 10
        return score

    def case_score(c):
        score = 0
        hay = " ".join([
            c.get("title", ""), c.get("issue", ""), c.get("ruling", ""),
            " ".join(c.get("tags", [])), c.get("category", ""),
        ]).lower()
        for word in q.split():
            if len(word) > 3 and word in hay:
                score += 2
        # Recent case boost
        if c.get("year", 0) >= 2020:
            score += 1
        return score

    top_sections = sorted(
        sections_data["sections"] + sections_data["special_acts"],
        key=section_score, reverse=True,
    )[:max_sections]
    top_sections = [s for s in top_sections if section_score(s) > 0]

    top_cases = sorted(cases_data["cases"], key=case_score, reverse=True)[:max_cases]
    top_cases = [c for c in top_cases if case_score(c) > 0]

    # Scenarios scoring
    def scenario_score(s):
        score = 0
        hay = " ".join([
            s.get("title", ""), s.get("category", ""),
            " ".join(s.get("keywords", [])),
            " ".join(s.get("applicable_law", [])),
        ]).lower()
        for word in q.split():
            if len(word) > 3 and word in hay:
                score += 3
        return score

    top_scenarios = sorted(scenarios_data["scenarios"], key=scenario_score, reverse=True)[:max_scenarios]
    top_scenarios = [s for s in top_scenarios if scenario_score(s) > 0]

    if not top_sections and not top_cases and not top_scenarios:
        return ""

    lines = ["\n\n=== VERIFIED LEGAL REFERENCE (use these, never hallucinate) ===\n"]
    if top_sections:
        lines.append("RELEVANT STATUTORY PROVISIONS:")
        for s in top_sections:
            ref = s.get("ipc") or s.get("code") or "?"
            bns = s.get("bns")
            ref_str = f"IPC {ref}" + (f" ↔ BNS {bns}" if bns else "")
            line = f"- {ref_str}: {s.get('title', '')}. Punishment: {s.get('punishment', '')}"
            if s.get("explanation"):
                line += f" | {s['explanation']}"
            if s.get("example"):
                line += f" | Example: {s['example']}"
            lines.append(line)

    if top_cases:
        lines.append("\nRELEVANT SUPREME COURT PRECEDENTS:")
        for c in top_cases:
            lines.append(f"- {c.get('title', '')} ({c.get('year', '')}, {c.get('citation', '')}): {c.get('ruling', '')[:240]}")

    if top_scenarios:
        lines.append("\nREAL-LIFE PROCEDURE FOR SIMILAR SITUATIONS (use this as the step-by-step backbone):")
        for sc in top_scenarios:
            lines.append(f"\nSCENARIO: {sc.get('title')}")
            lines.append(f"  Applicable laws: {', '.join(sc.get('applicable_law', []))}")
            for i, step in enumerate(sc.get("procedure", []), 1):
                lines.append(f"  Step {i}: {step}")
            if sc.get("remedies"):
                lines.append(f"  Remedies: {', '.join(sc['remedies'])}")
            if sc.get("tip"):
                lines.append(f"  Practical tip: {sc['tip']}")

    lines.append("\nWhen you cite, use these EXACT references. Mix the procedure steps with your answer to be practical and complete.\n")
    return "\n".join(lines)


def _get_or_create_session(db: DBSession, req: LegalQuery) -> ChatSession:
    if req.session_id:
        session = db.get(ChatSession, req.session_id)
        if session:
            return session
    session = ChatSession(
        device_id=req.device_id,
        title=req.query[:60],
        state=req.state,
        language=req.language,
    )
    db.add(session)
    db.flush()
    return session


@router.post("/query", response_model=ChatApiResponse)
@limiter.limit("30/minute")
async def ask_legal_question(
    request: Request,
    req: LegalQuery,
    db: DBSession = Depends(get_db),
):
    session = _get_or_create_session(db, req)

    user_msg = Message(session_id=session.id, role="user", content=req.query)
    db.add(user_msg)

    grounding = _ground_with_laws(req.query)

    # If user asks about today's/recent cases — inject TOP recent landmark cases
    if _wants_recent_news(req.query):
        cases_data = _load_cases()
        recent = sorted(
            [c for c in cases_data["cases"] if c.get("year", 0) >= 2023],
            key=lambda c: c.get("year", 0), reverse=True,
        )[:6]
        if recent:
            grounding += "\n\nTODAY-FOCUSED CONTEXT — user is asking about recent/today's cases. Summarize these 5 most-recent SC judgments instead of greeting:\n"
            for c in recent:
                grounding += f"\n• {c['title']} ({c['year']}, {c.get('citation', '')}): {c.get('ruling', '')[:200]}"
            grounding += "\n\nIn your reply, give a numbered list of these 5 recent cases with 1-2 line summary each. Don't ask the user what they want — directly give the brief."

    prompt = CHAT_SYSTEM_PROMPT.format(
        state=req.state, language=req.language, query=req.query
    ) + grounding
    fallback = {
        "text": "I couldn't process that fully. Please rephrase your question.",
        "citations": [],
        "alerts": [],
    }

    try:
        data = await generate_json(prompt, fallback)
    except GeminiError as exc:
        log.error("chat_failed", error=str(exc))
        # Still persist the user message and surface a readable assistant reply
        err_text = str(exc) or "AI service is temporarily unavailable. Please try again."
        ai_err = Message(session_id=session.id, role="assistant", content=err_text)
        db.add(ai_err)
        db.commit()
        return ChatApiResponse(
            status="error",
            session_id=session.id,
            message=err_text,
            response=ChatResponse(text=err_text),
        )

    chat_resp = ChatResponse(
        text=str(data.get("text", "")).strip() or fallback["text"],
        citations=data.get("citations") or [],
        alerts=data.get("alerts") or [],
    )

    ai_msg = Message(
        session_id=session.id,
        role="assistant",
        content=chat_resp.text,
        citations=[c.model_dump() for c in chat_resp.citations],
        alerts=[a.model_dump() for a in chat_resp.alerts],
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    log.info("chat_ok", session_id=session.id, msg_id=ai_msg.id)

    return ChatApiResponse(
        status="success",
        session_id=session.id,
        message_id=ai_msg.id,
        response=chat_resp,
    )
