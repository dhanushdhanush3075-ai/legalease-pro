"""
Core features (no AI) — emergency cards, dictionary, police stations.
All static data, all offline-friendly.
"""
import json
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/core", tags=["core"])
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def _emergency() -> dict:
    with open(DATA_DIR / "emergency_cards.json", "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _dictionary() -> dict:
    with open(DATA_DIR / "dictionary.json", "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _stations() -> dict:
    with open(DATA_DIR / "police_stations.json", "r", encoding="utf-8") as f:
        return json.load(f)


# ----- Emergency cards -----
@router.get("/emergency-cards")
def list_emergency_cards():
    return _emergency()


@router.get("/emergency-cards/{card_id}")
def get_emergency_card(card_id: str):
    for c in _emergency()["cards"]:
        if c["id"] == card_id:
            return c
    raise HTTPException(status_code=404, detail="Card not found")


# ----- Legal dictionary -----
@router.get("/dictionary")
def search_dictionary(q: str = "", category: str | None = None, limit: int = Query(80, ge=1, le=300)):
    data = _dictionary()
    terms = data["terms"]
    qn = (q or "").lower().strip()

    def keep(t):
        if category and category.lower() not in (t.get("category", "")).lower():
            return False
        if not qn:
            return True
        hay = (t.get("term", "") + " " + t.get("en", "") + " " + t.get("ta", "") + " " + t.get("hi", "") + " " + t.get("category", "")).lower()
        return qn in hay

    results = [t for t in terms if keep(t)]
    results.sort(key=lambda t: t.get("term", "").lower())
    return {"meta": data["meta"], "count": len(results), "terms": results[:limit]}


@router.get("/dictionary/categories")
def list_dict_categories():
    return sorted({t.get("category", "") for t in _dictionary()["terms"] if t.get("category")})


# ----- Police stations -----
@router.get("/police-stations")
def list_police_stations(
    state: str | None = None,
    district: str | None = None,
    q: str = "",
    limit: int = Query(100, ge=1, le=300),
):
    data = _stations()
    items = data["stations"]
    qn = (q or "").lower().strip()

    def keep(s):
        if state and state.lower() not in (s.get("state", "")).lower():
            return False
        if district and district.lower() not in (s.get("district", "")).lower():
            return False
        if not qn:
            return True
        hay = (s.get("name", "") + " " + s.get("address", "") + " " + s.get("state", "") + " " + s.get("district", "")).lower()
        return qn in hay

    results = [s for s in items if keep(s)]
    return {"meta": data["meta"], "count": len(results), "stations": results[:limit]}


@router.get("/police-stations/states")
def list_ps_states():
    return sorted({s["state"] for s in _stations()["stations"]})
