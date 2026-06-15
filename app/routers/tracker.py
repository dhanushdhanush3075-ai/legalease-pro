"""
Case Tracker — deep-links into eCourts CNR / case status portal.

eCourts does NOT expose a public free API, but its services are CNR-based so we
can build the canonical deep links the user can open in a browser. The CNR is
a 16-character unique identifier assigned to every Indian case.
"""
from urllib.parse import quote
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/tracker", tags=["tracker"])


def _classify_cnr(cnr: str) -> dict:
    """Light validation. CNR format: state_code(2) + district_code(2) + court_code(4) + year(4) + serial(4)."""
    cnr = cnr.replace("-", "").replace(" ", "").upper()
    if len(cnr) != 16:
        return {"valid": False, "reason": "CNR must be exactly 16 characters (letters+digits)."}
    state_code = cnr[:2]
    return {
        "valid": True,
        "cnr": cnr,
        "state_code": state_code,
        "district_code": cnr[2:4],
        "court_code": cnr[4:8],
        "year": cnr[8:12],
        "serial": cnr[12:16],
    }


@router.get("/cnr")
def lookup_cnr(cnr: str = Query(..., min_length=10, max_length=24)):
    info = _classify_cnr(cnr)
    if not info["valid"]:
        return {"status": "invalid", "message": info.get("reason", "Invalid CNR")}
    clean = info["cnr"]
    return {
        "status": "ok",
        "cnr": clean,
        "year": info["year"],
        "links": {
            "ecourts_district": f"https://services.ecourts.gov.in/ecourtindia_v6/?p=cnr_status/searchByCNR&cino={clean}",
            "ecourts_high_court": f"https://hcservices.ecourts.gov.in/hcservices/main.php?cnr_no={clean}",
            "supreme_court_case_status": f"https://www.sci.gov.in/case-status/",
            "indian_kanoon_search": f"https://indiankanoon.org/search/?formInput={clean}",
        },
        "message": "Use any link above to view live case status. The first one (district eCourts) covers most cases.",
    }


@router.get("/by-party")
def search_by_party(name: str = Query(..., min_length=3, max_length=200), state: str | None = None):
    """Build a deep-link search by petitioner / respondent name."""
    q = quote(name)
    return {
        "status": "ok",
        "name": name,
        "state": state,
        "links": {
            "ecourts_party_search": "https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/index",
            "ecourts_act_search": "https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/act_search",
            "indian_kanoon": f"https://indiankanoon.org/search/?formInput={q}",
            "supreme_court": f"https://www.sci.gov.in/case-status/?term={q}",
        },
        "note": "eCourts requires CAPTCHA so direct API call isn't possible — open the links to search interactively.",
    }
