import json
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/courts", tags=["courts"])
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def _load() -> dict:
    with open(DATA_DIR / "courts.json", "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/")
def list_courts(
    state: str | None = None,
    city: str | None = None,
    type: str | None = Query(default=None, alias="type"),
    q: str = "",
    limit: int = Query(60, ge=1, le=200),
):
    data = _load()
    items = data["courts"]
    qn = q.lower().strip()

    def keep(c):
        if state and state.lower() not in c.get("state", "").lower():
            return False
        if city and city.lower() not in c.get("city", "").lower():
            return False
        if type and type.lower() not in c.get("type", "").lower():
            return False
        if qn:
            hay = " ".join([c.get("name", ""), c.get("state", ""), c.get("city", ""), c.get("jurisdiction", ""), c.get("type", "")]).lower()
            return qn in hay
        return True

    results = [c for c in items if keep(c)]
    return {"meta": data["meta"], "count": len(results), "courts": results[:limit]}


@router.get("/{court_id}")
def get_court(court_id: str):
    for c in _load()["courts"]:
        if c.get("id") == court_id:
            return c
    raise HTTPException(status_code=404, detail="Court not found")


@router.get("/states/list")
def list_states():
    data = _load()
    return sorted({c["state"] for c in data["courts"] if c.get("state")})
