"""
Legal calculators:
1. Bail check — is a section bailable / non-bailable?
2. Limitation period — when does my claim expire?
3. Court fee — by state + claim value
"""
from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/api/calc", tags=["calculators"])


# ---------- Bailability ----------
# Common Indian offences — bailable / non-bailable / cognizable status
BAIL_MAP: dict[str, dict] = {
    # IPC
    "279": {"bailable": True, "cognizable": True, "court": "Any Magistrate", "title": "Rash driving"},
    "302": {"bailable": False, "cognizable": True, "court": "Court of Session", "title": "Murder"},
    "304": {"bailable": False, "cognizable": True, "court": "Court of Session", "title": "Culpable homicide not amounting to murder"},
    "304A": {"bailable": True, "cognizable": True, "court": "JM First Class", "title": "Death by negligence"},
    "306": {"bailable": False, "cognizable": True, "court": "Court of Session", "title": "Abetment of suicide"},
    "307": {"bailable": False, "cognizable": True, "court": "Court of Session", "title": "Attempt to murder"},
    "323": {"bailable": True, "cognizable": False, "court": "Any Magistrate", "title": "Voluntarily causing hurt"},
    "325": {"bailable": True, "cognizable": True, "court": "JM First Class", "title": "Grievous hurt"},
    "326": {"bailable": False, "cognizable": True, "court": "Court of Session", "title": "Grievous hurt by dangerous weapon"},
    "326A": {"bailable": False, "cognizable": True, "court": "Court of Session", "title": "Acid attack"},
    "354": {"bailable": False, "cognizable": True, "court": "Magistrate / Sessions", "title": "Outraging modesty"},
    "354A": {"bailable": True, "cognizable": True, "court": "Magistrate", "title": "Sexual harassment"},
    "354D": {"bailable": True, "cognizable": True, "court": "Magistrate", "title": "Stalking (1st offence)"},
    "363": {"bailable": True, "cognizable": True, "court": "JM First Class", "title": "Kidnapping"},
    "376": {"bailable": False, "cognizable": True, "court": "Court of Session", "title": "Rape"},
    "379": {"bailable": True, "cognizable": True, "court": "Any Magistrate", "title": "Theft"},
    "380": {"bailable": False, "cognizable": True, "court": "Magistrate", "title": "Theft in dwelling house"},
    "384": {"bailable": True, "cognizable": True, "court": "JM First Class", "title": "Extortion"},
    "392": {"bailable": False, "cognizable": True, "court": "Magistrate / Sessions", "title": "Robbery"},
    "395": {"bailable": False, "cognizable": True, "court": "Court of Session", "title": "Dacoity"},
    "406": {"bailable": True, "cognizable": True, "court": "Magistrate", "title": "Criminal breach of trust"},
    "420": {"bailable": True, "cognizable": True, "court": "Magistrate", "title": "Cheating"},
    "498A": {"bailable": True, "cognizable": True, "court": "Magistrate", "title": "Cruelty by husband"},
    "506": {"bailable": True, "cognizable": False, "court": "Any Magistrate", "title": "Criminal intimidation"},

    # Special Acts
    "138NI": {"bailable": True, "cognizable": False, "court": "JM First Class", "title": "Cheque bounce (NI Act)"},
    "66IT": {"bailable": True, "cognizable": True, "court": "Magistrate", "title": "Hacking (IT Act 66)"},
    "66CIT": {"bailable": True, "cognizable": True, "court": "Magistrate", "title": "Identity theft (IT Act 66C)"},
    "67IT": {"bailable": False, "cognizable": True, "court": "Court of Session", "title": "Online obscenity (IT Act 67)"},
    "POCSO7": {"bailable": False, "cognizable": True, "court": "POCSO Special Court", "title": "Sexual assault on child"},
    "NDPS20": {"bailable": False, "cognizable": True, "court": "Special NDPS Court", "title": "NDPS commercial quantity"},
    "DV12": {"bailable": True, "cognizable": False, "court": "Magistrate (DV Act)", "title": "Domestic Violence Act application"},
}


@router.get("/bail")
def check_bail(section: str = Query(..., min_length=1, max_length=16)):
    """Check if an IPC/BNS/special-act section is bailable."""
    key = section.upper().replace(" ", "").replace("IPC", "").replace("BNS", "").replace("SEC", "")
    info = BAIL_MAP.get(key) or BAIL_MAP.get(section.upper())
    if not info:
        return {
            "status": "unknown",
            "section": section,
            "message": "Section not in our database. Consult an advocate or check the First Schedule of CrPC/BNSS.",
        }
    return {
        "status": "known",
        "section": section,
        "title": info["title"],
        "bailable": info["bailable"],
        "cognizable": info["cognizable"],
        "court": info["court"],
        "summary": (
            f"{info['title']} — "
            f"{'BAILABLE' if info['bailable'] else 'NON-BAILABLE'}, "
            f"{'COGNIZABLE' if info['cognizable'] else 'NON-COGNIZABLE'}. "
            f"Triable by {info['court']}."
        ),
    }


# ---------- Limitation periods (Limitation Act 1963) ----------
LIMITATION = [
    {"id": "money-suit", "category": "Civil", "title": "Suit for money lent (oral / written)", "period_years": 3, "note": "From date of loan or due date of repayment"},
    {"id": "promissory-note", "category": "Civil", "title": "Suit on a promissory note", "period_years": 3, "note": "From date when note is payable"},
    {"id": "bill-exchange", "category": "Civil", "title": "Suit on a bill of exchange", "period_years": 3, "note": "From date when bill payable"},
    {"id": "movable-property", "category": "Civil", "title": "Suit for movable property", "period_years": 3, "note": "From when defendant takes possession"},
    {"id": "immovable-property", "category": "Civil", "title": "Suit for possession of immovable property (private)", "period_years": 12, "note": "From when possession becomes adverse"},
    {"id": "immovable-govt", "category": "Civil", "title": "Suit for immovable property (Govt)", "period_years": 30, "note": "From accrual of right"},
    {"id": "specific-performance", "category": "Civil", "title": "Specific performance of contract", "period_years": 3, "note": "From date fixed for performance"},
    {"id": "rescind-contract", "category": "Civil", "title": "Suit to rescind a contract", "period_years": 3, "note": "From when ground arose"},
    {"id": "tort-defamation", "category": "Civil", "title": "Tort — defamation", "period_years": 1, "note": "From date of publication"},
    {"id": "tort-personal-injury", "category": "Civil", "title": "Tort — personal injury / negligence", "period_years": 1, "note": "From date of injury"},
    {"id": "tort-trespass", "category": "Civil", "title": "Trespass to person / property", "period_years": 3, "note": "From date of trespass"},
    {"id": "appeal-hc", "category": "Appeal", "title": "Civil appeal to High Court", "period_days": 90, "note": "From date of decree"},
    {"id": "appeal-lower", "category": "Appeal", "title": "Civil appeal to subordinate court", "period_days": 30, "note": "From date of decree"},
    {"id": "appeal-sc", "category": "Appeal", "title": "SLP to Supreme Court", "period_days": 90, "note": "From date of HC order"},
    {"id": "review-civil", "category": "Civil", "title": "Review of civil judgment", "period_days": 30, "note": "From date of decree"},
    {"id": "execution-decree", "category": "Civil", "title": "Execution of decree", "period_years": 12, "note": "From date of decree"},
    {"id": "consumer-complaint", "category": "Consumer", "title": "Consumer complaint (CPA 2019)", "period_years": 2, "note": "From cause of action; condonable on sufficient cause"},
    {"id": "cheque-138", "category": "Criminal", "title": "Section 138 NI Act complaint", "period_days": 30, "note": "Notice within 30 days of return memo; complaint within 30 days after expiry of 15-day notice"},
    {"id": "fir-cognizable", "category": "Criminal", "title": "Filing FIR (cognizable offence)", "period_years": None, "note": "No bar for cognizable offences (s 154 CrPC), but practical delay may be questioned"},
    {"id": "rti-appeal-first", "category": "RTI", "title": "First RTI appeal", "period_days": 30, "note": "From date of receipt of CPIO decision"},
    {"id": "rti-appeal-second", "category": "RTI", "title": "Second RTI appeal (to Information Commission)", "period_days": 90, "note": "From date of first appeal decision"},
    {"id": "lobour-id-act", "category": "Labour", "title": "Industrial Disputes — claim of dues", "period_years": 1, "note": "From date dues became payable"},
]


@router.get("/limitation")
def list_limitation(q: str = "", category: str | None = None):
    qn = q.lower().strip()

    def keep(item):
        if category and category.lower() != item["category"].lower():
            return False
        if not qn:
            return True
        return qn in (item["title"] + " " + item.get("note", "") + " " + item["category"]).lower()
    return {"items": [i for i in LIMITATION if keep(i)]}


# ---------- Court fee ----------
# Simplified — actual stamp duty varies. Returns approximate range with disclaimer.

COURT_FEE_RULES = {
    "Tamil Nadu": {
        "tier": [
            (0, 100, "₹0.50"),
            (100, 1_000, "1% of claim"),
            (1_000, 10_000, "2% of claim"),
            (10_000, 50_000, "3% of claim"),
            (50_000, 1_00_000, "4% of claim"),
            (1_00_000, 10_00_000, "5% of claim"),
        ],
        "max_fee": "₹3,00,000 (capped)",
        "act": "Court Fees Act 1955 (TN)",
    },
    "Maharashtra": {
        "tier": [
            (0, 1_000, "2% of claim"),
            (1_000, 50_000, "4% of claim"),
            (50_000, 1_00_000, "5% of claim"),
            (1_00_000, 10_00_000, "6% of claim"),
        ],
        "max_fee": "₹3,75,000",
        "act": "Maharashtra Court Fees Act 1959",
    },
    "Karnataka": {
        "tier": [
            (0, 50_000, "5% of claim"),
            (50_000, 5_00_000, "5% of claim"),
            (5_00_000, 1_00_00_000, "5% of claim"),
        ],
        "max_fee": "₹5,00,000",
        "act": "Karnataka Court Fees & Suits Valuation Act 1958",
    },
    "Delhi": {
        "tier": [
            (0, 5_000, "Standard slab ₹5 to ₹500"),
            (5_000, 50_000, "5% of claim"),
            (50_000, 5_00_000, "5% of claim"),
        ],
        "max_fee": "Capped per schedule",
        "act": "Court Fees Act 1870 (Delhi)",
    },
    "default": {
        "tier": [
            (0, 100_000, "Approx 2-5% of claim"),
            (100_000, 10_00_000, "Approx 5-7% of claim"),
        ],
        "max_fee": "Varies by state",
        "act": "Court Fees Act 1870 (default fallback)",
    },
}


@router.get("/court-fee")
def court_fee(state: str = "default", claim_value: float = Query(0, ge=0)):
    rules = COURT_FEE_RULES.get(state) or COURT_FEE_RULES["default"]
    applicable = None
    for low, high, rate in rules["tier"]:
        if low <= claim_value < high:
            applicable = rate
            break
    if applicable is None:
        applicable = rules["tier"][-1][2]

    # rough numeric estimate
    pct = None
    if "%" in applicable:
        try:
            pct = float(applicable.split("%")[0].split()[-1])
        except ValueError:
            pct = None
    estimate = None
    if pct is not None and claim_value > 0:
        estimate = round((claim_value * pct) / 100, 2)

    return {
        "state": state,
        "claim_value": claim_value,
        "applicable_slab": applicable,
        "estimate_inr": estimate,
        "max_fee": rules["max_fee"],
        "act": rules["act"],
        "disclaimer": "This is an indicative estimate. Actual court fee can vary by case type (civil, family, consumer), valuation method, and state amendments. Verify with court reckoner before filing.",
    }


@router.get("/court-fee/states")
def court_fee_states():
    return [s for s in COURT_FEE_RULES.keys() if s != "default"]
