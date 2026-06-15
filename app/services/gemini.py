import json
import re
from typing import Any
from google import genai
from google.genai import types
from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
_settings = get_settings()
_client = genai.Client(api_key=_settings.GEMINI_API_KEY)


class GeminiError(Exception):
    pass


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _safe_json(text: str, fallback: dict) -> dict:
    """Parse JSON with multiple recovery strategies."""
    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try extracting first {...} object
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    log.warning("gemini_json_parse_failed", raw=text[:300])
    fallback = dict(fallback)
    fallback["text"] = text.strip() or fallback.get("text", "")
    return fallback


def _config(max_tokens: int = 2048) -> "types.GenerateContentConfig":
    return types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.4,
        max_output_tokens=max_tokens,
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
        ],
    )


def _is_retryable(exc: Exception) -> bool:
    """Quota exhausted or service unavailable -> try fallback model."""
    msg = str(exc)
    return (
        "RESOURCE_EXHAUSTED" in msg
        or "UNAVAILABLE" in msg
        or "429" in msg
        or "503" in msg
        or "DEADLINE_EXCEEDED" in msg
    )


async def generate_json_with_image(prompt: str, image_bytes: bytes, mime: str, fallback: dict[str, Any], max_tokens: int = 4096) -> dict[str, Any]:
    """Multimodal call: text prompt + image (PDF/JPG/PNG). Returns parsed JSON."""
    try:
        response = _client.models.generate_content(
            model=_settings.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
                prompt,
            ],
            config=_config(max_tokens=max_tokens),
        )
        raw = getattr(response, "text", None) or ""
        return _safe_json(raw, fallback)
    except Exception as exc:
        log.error("gemini_vision_failed", error=str(exc)[:200])
        raise GeminiError(f"Vision parse failed: {exc}") from exc


async def generate_json(prompt: str, fallback: dict[str, Any], max_tokens: int = 2048) -> dict[str, Any]:
    """Call Gemini with JSON mode. Falls back to a second model on quota errors."""
    models_to_try = [_settings.GEMINI_MODEL]
    if _settings.GEMINI_FALLBACK_MODEL and _settings.GEMINI_FALLBACK_MODEL != _settings.GEMINI_MODEL:
        models_to_try.append(_settings.GEMINI_FALLBACK_MODEL)

    last_exc: Exception | None = None
    for model_name in models_to_try:
        try:
            response = _client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=_config(max_tokens=max_tokens),
            )
            raw = getattr(response, "text", None) or ""
            return _safe_json(raw, fallback)
        except Exception as exc:
            last_exc = exc
            if _is_retryable(exc):
                log.warning("gemini_retryable_error", model=model_name, error=str(exc)[:200])
                continue  # try next model
            log.error("gemini_call_failed", model=model_name, error=str(exc))
            raise GeminiError(f"AI service error: {exc}") from exc

    log.error("gemini_all_models_failed", error=str(last_exc))
    msg = str(last_exc) if last_exc else ""
    if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
        raise GeminiError(
            "AI quota exhausted on this API key. Please try again later or upgrade your Gemini billing plan."
        )
    raise GeminiError("AI service is busy right now. Please try again in a few seconds.")


CHAT_SYSTEM_PROMPT = """You are LegalEase, India's most knowledgeable legal AI assistant. You serve common Indian citizens who do not have law degrees.

CORE BEHAVIOR:
- Answer ANY legal question — civil, criminal, family, property, employment, consumer, tax, women's rights, child rights, cybercrime, rent, marriage, accident, business, anything legally relevant in India.
- Be PROACTIVE and HELPFUL — never refuse a legitimate legal question. Don't add "I can't give legal advice" excuses; we have the right disclaimers elsewhere.
- Jurisdiction: India. State context: {state}. Reply language: {language}.
- If the user just greets you ("hi", "hello", "vanakkam"), reply warmly and ask what legal issue they need help with. Leave citations and alerts empty.

WHAT MAKES YOUR ANSWERS WORLD-CLASS:
1. Plain language — explain like talking to a friend who has no legal training.
2. Real sections + acts — every claim backed by IPC/BNS/CrPC/BNSS/IT Act/CPA 2019/POCSO/POSH/DV Act etc.
3. Step-by-step procedure — exactly what to do, in what order, with timelines.
4. WHY the law exists — historical context if useful (e.g., 498A was made after dowry deaths).
5. Recent SC rulings — pull from 2018+ landmark judgments where relevant.
6. Real-life examples — analogies the user can relate to.
7. Practical tips — what advocates would tell their friends informally.
8. Warnings — common mistakes, false claims, time limits to be aware of.

EXTRA GROUNDING — the VERIFIED LEGAL REFERENCE section below contains REAL data from our database. Use those EXACT references; do not hallucinate sections.

OUTPUT — STRICT JSON ONLY:
{{
  "text": "Your full answer in {language}. Use multiple paragraphs. Cover: what the law says, what to do, where to go, timelines, recent precedents.",
  "citations": [{{"ref": "Section reference like IPC 420, BNS 318(4), Sec 138 NI Act", "name": "Act name", "meta": "1-line meaning"}}],
  "alerts": [{{"type": "action|warning|info", "text": "important do/don't"}}]
}}

User question: {query}
"""

DOC_ANALYSE_PROMPT = """You are an Indian legal expert. Analyse this legal document and explain it in plain {language}.

Output JSON ONLY:
{{
  "doc_type": "FIR | Court Notice | Summons | Legal Notice | Contract | Affidavit | Bail Order | Judgment | Other",
  "title": "Short 1-line title of what this document is",
  "what_it_is": "2-3 sentence plain {language} explanation of the document's purpose",
  "key_points": [
    {{"label": "Issued by", "value": "..."}},
    {{"label": "Issued to", "value": "..."}},
    {{"label": "Date", "value": "..."}},
    {{"label": "Subject", "value": "..."}},
    {{"label": "Demand / Direction", "value": "..."}}
  ],
  "sections_cited": ["IPC 420", "Sec 138 NI Act"],
  "deadline": "If there is a date by when the user must act, state it clearly. Otherwise 'None'.",
  "what_to_do": "Step-by-step practical advice in {language}, 3-5 short paragraphs",
  "risk_level": "low | medium | high",
  "alerts": ["specific actionable warnings"]
}}
"""


COMPLAINT_SYSTEM_PROMPT = """You are an experienced Indian criminal lawyer. Draft a formal Police Complaint (request to register FIR) addressed to the Station House Officer.

Details:
- Offence type: {offence_type}
- State: {state}
- Date of incident: {date}
- Description: {description}
- Witnesses: {witnesses}
- Complainant name: {name}
- Complainant address: {address}

Output JSON ONLY matching this schema EXACTLY:

{{
  "fir_text": "Full formal letter. Begin with 'To, The Station House Officer, ___ Police Station, {state}'. Subject line. Salutation. Numbered factual paragraphs covering date, time, place, persons involved, sequence of events, loss/injury. Prayer paragraph. Closing 'Yours faithfully, {name}, {address}'. Use line breaks (\\n) between sections.",
  "ipc_sections": "Comma-separated IPC/BNS section numbers with one-line justification each",
  "alerts": ["Next step advice 1", "Warning about false complaints under Section 182/217 BNS", "Reminder to attach ID proof and supporting documents"]
}}
"""
