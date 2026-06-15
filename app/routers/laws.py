import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
import urllib.request

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(prefix="/api/laws", tags=["laws"])
log = get_logger(__name__)
settings = get_settings()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def _load_sections() -> dict:
    with open(DATA_DIR / "ipc_bns_map.json", "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_cases() -> dict:
    with open(DATA_DIR / "landmark_cases.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _norm(s: str) -> str:
    return (s or "").strip().lower()


# ---------- Section lookup ----------

@router.get("/section")
def search_sections(
    q: str = Query("", max_length=128),
    code: str | None = Query(default=None, description="ipc | bns | special"),
    category: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    data = _load_sections()
    sections = list(data["sections"])
    specials = list(data["special_acts"])

    qn = _norm(q)
    # Tokenize numeric search like "302" or "IPC 302" or "BNS 103"
    num_match = re.findall(r"\d+[A-Za-z]*", qn)

    def matches_section(item):
        if not qn:
            return True
        hay = " ".join([
            item.get("ipc", ""), item.get("bns", ""),
            item.get("title", ""), item.get("category", ""),
            " ".join(item.get("keywords", [])),
        ]).lower()
        if qn in hay:
            return True
        for n in num_match:
            if n in (item.get("ipc", "") or "").lower() or n in (item.get("bns", "") or "").lower():
                return True
        return False

    def matches_special(item):
        if not qn:
            return True
        hay = " ".join([
            item.get("code", ""), item.get("name", ""),
            item.get("title", ""), " ".join(item.get("keywords", [])),
        ]).lower()
        return qn in hay

    s_results = [s for s in sections if matches_section(s)]
    sp_results = [s for s in specials if matches_special(s)]

    if category:
        cn = _norm(category)
        s_results = [s for s in s_results if cn in _norm(s.get("category", ""))]

    if code == "ipc":
        sp_results = []
    elif code == "bns":
        sp_results = []
    elif code == "special":
        s_results = []

    return {
        "meta": data["meta"],
        "query": q,
        "count": len(s_results) + len(sp_results),
        "ipc_bns": s_results[:limit],
        "special_acts": sp_results[:limit],
    }


@router.get("/section/by-ipc/{number}")
def section_by_ipc(number: str):
    data = _load_sections()
    n = number.upper()
    for s in data["sections"]:
        if (s.get("ipc") or "").upper() == n:
            return s
    raise HTTPException(status_code=404, detail=f"IPC section {number} not in database")


@router.get("/section/by-bns/{number}")
def section_by_bns(number: str):
    data = _load_sections()
    n = number.upper()
    for s in data["sections"]:
        if (s.get("bns") or "").upper().startswith(n):
            return s
    raise HTTPException(status_code=404, detail=f"BNS section {number} not in database")


# ---------- Landmark cases ----------

@router.get("/landmark")
def list_landmark_cases(
    q: str = Query("", max_length=128),
    category: str | None = None,
    year_from: int | None = Query(default=None, ge=1900, le=2100),
    year_to: int | None = Query(default=None, ge=1900, le=2100),
    limit: int = Query(60, ge=1, le=200),
):
    data = _load_cases()
    cases = data["cases"]
    qn = _norm(q)

    def keep(c):
        if year_from and c.get("year", 0) < year_from:
            return False
        if year_to and c.get("year", 0) > year_to:
            return False
        if category and _norm(category) not in _norm(c.get("category", "")):
            return False
        if not qn:
            return True
        hay = " ".join([
            c.get("title", ""), c.get("citation", ""), c.get("issue", ""),
            c.get("ruling", ""), c.get("category", ""),
            " ".join(c.get("tags", [])),
        ]).lower()
        return qn in hay

    results = sorted([c for c in cases if keep(c)], key=lambda c: c.get("year", 0), reverse=True)
    return {"meta": data["meta"], "count": len(results), "cases": results[:limit]}


@router.get("/landmark/{case_id}")
def get_landmark_case(case_id: str):
    data = _load_cases()
    for c in data["cases"]:
        if c.get("id") == case_id:
            return c
    raise HTTPException(status_code=404, detail="Case not found")


# ---------- Indian Kanoon live search (public website search) ----------

@router.get("/cases/search")
def search_cases(q: str = Query(..., min_length=2, max_length=200), limit: int = Query(20, ge=1, le=50)):
    """
    Searches Indian Kanoon. If INDIAN_KANOON_API_TOKEN is set, uses their API;
    otherwise returns deep-links into Indian Kanoon search UI as fallback.
    """
    if settings.INDIAN_KANOON_API_TOKEN:
        try:
            url = f"https://api.indiankanoon.org/search/?formInput={quote(q)}&pagenum=0"
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Token {settings.INDIAN_KANOON_API_TOKEN}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            docs = payload.get("docs", [])[:limit]
            return {
                "source": "indiankanoon-api",
                "query": q,
                "count": len(docs),
                "results": [
                    {
                        "id": d.get("tid"),
                        "title": d.get("title", "").strip(),
                        "court": d.get("docsource") or d.get("court"),
                        "date": d.get("publishdate"),
                        "snippet": (d.get("headline", "") or "").strip(),
                        "url": f"https://indiankanoon.org/doc/{d.get('tid')}/",
                    }
                    for d in docs
                ],
            }
        except Exception as exc:
            log.error("kanoon_api_failed", error=str(exc))

    # Fallback: deep-link to Indian Kanoon search (no API key needed)
    return {
        "source": "indiankanoon-deeplink",
        "query": q,
        "count": 1,
        "note": "Open the link to see live results on Indian Kanoon. For embedded results, add INDIAN_KANOON_API_TOKEN to .env.",
        "results": [
            {
                "id": "kanoon-search",
                "title": f"Indian Kanoon search: {q}",
                "court": "Live database (Supreme Court, High Courts, Tribunals)",
                "date": "live",
                "snippet": "Click to open Indian Kanoon search results in a new tab.",
                "url": f"https://indiankanoon.org/search/?formInput={quote(q)}",
            }
        ],
    }


@router.get("/meta")
def meta():
    return {
        "sections": _load_sections()["meta"],
        "landmark": _load_cases()["meta"],
        "kanoon_api": bool(settings.INDIAN_KANOON_API_TOKEN),
    }
