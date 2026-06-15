import json
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/lawyers", tags=["lawyers"])
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def _load() -> dict:
    with open(DATA_DIR / "lawyers.json", "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/")
def list_lawyers(
    state: str | None = None,
    type: str | None = Query(default=None, description="SLSA | DLSA | NGO | Bar Association"),
    specialization: str | None = None,
    q: str = "",
    limit: int = Query(60, ge=1, le=200),
):
    data = _load()
    entries = data["entries"]
    qn = q.lower().strip()

    def keep(e):
        if state and state.lower() not in e.get("state", "").lower() and e.get("state", "").lower() != "all india":
            return False
        if type and type.lower() != e.get("type", "").lower():
            return False
        if specialization:
            specs = [s.lower() for s in e.get("specialization", [])]
            if specialization.lower() not in specs and "all" not in specs:
                return False
        if qn:
            hay = " ".join([e.get("name", ""), e.get("state", ""), e.get("type", ""), " ".join(e.get("specialization", []))]).lower()
            return qn in hay
        return True

    results = [e for e in entries if keep(e)]
    return {
        "meta": data["meta"],
        "count": len(results),
        "entries": results[:limit],
    }


@router.get("/helplines")
def helplines():
    """All emergency / legal aid helpline numbers."""
    data = _load()
    return {k: v for k, v in data["meta"].items() if k.startswith("helpline_")}
