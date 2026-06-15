from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.services.gemini import generate_json, GeminiError

router = APIRouter(prefix="/api/templates", tags=["templates"])
log = get_logger(__name__)


FIELD_DEFS = {
    "landlord_name":     {"label": "Landlord's full name", "type": "text", "required": True},
    "tenant_name":       {"label": "Tenant's full name", "type": "text", "required": True},
    "property_address":  {"label": "Property address", "type": "textarea", "required": True},
    "rent":              {"label": "Monthly rent (₹)", "type": "number", "required": True},
    "deposit":           {"label": "Security deposit (₹)", "type": "number", "required": True},
    "start_date":        {"label": "Lease start date", "type": "date", "required": True},
    "public_authority":  {"label": "Public Authority (department)", "type": "text", "required": True},
    "subject":           {"label": "Subject of request", "type": "text", "required": True},
    "information_sought":{"label": "Information you need (be specific)", "type": "textarea", "required": True},
    "applicant_name":    {"label": "Your full name", "type": "text", "required": True},
    "address":           {"label": "Your address", "type": "textarea", "required": True},
    "recipient_name":    {"label": "Recipient's name", "type": "text", "required": True},
    "recipient_address": {"label": "Recipient's address", "type": "textarea", "required": True},
    "facts":             {"label": "Facts / what happened", "type": "textarea", "required": True},
    "demand":            {"label": "What you demand (compensation, action, etc.)", "type": "textarea", "required": True},
    "sender_name":       {"label": "Your full name (sender)", "type": "text", "required": True},
    "company_name":      {"label": "Company / seller name", "type": "text", "required": True},
    "product":           {"label": "Product / service bought", "type": "text", "required": True},
    "purchase_date":     {"label": "Date of purchase", "type": "date", "required": True},
    "complaint_details": {"label": "What's wrong (defect, deficiency)", "type": "textarea", "required": True},
    "relief_sought":     {"label": "What you want (refund / replacement / damages)", "type": "textarea", "required": True},
    "complainant_name":  {"label": "Your full name", "type": "text", "required": True},
    "drawer_name":       {"label": "Drawer's name (who gave you the cheque)", "type": "text", "required": True},
    "drawer_address":    {"label": "Drawer's address", "type": "textarea", "required": True},
    "cheque_number":     {"label": "Cheque number", "type": "text", "required": True},
    "cheque_date":       {"label": "Cheque date", "type": "date", "required": True},
    "amount":            {"label": "Amount (₹)", "type": "number", "required": True},
    "bank":              {"label": "Bank name & branch", "type": "text", "required": True},
    "dishonour_date":    {"label": "Date cheque dishonoured", "type": "date", "required": True},
    "testator_name":     {"label": "Your full name (testator)", "type": "text", "required": True},
    "beneficiaries":     {"label": "Beneficiaries (names + relationship + share)", "type": "textarea", "required": True},
    "assets":            {"label": "Assets list (property / accounts / belongings)", "type": "textarea", "required": True},
    "executor":          {"label": "Executor's name (who will carry out the will)", "type": "text", "required": True},
    "offence_type":      {"label": "Type of offence", "type": "text", "required": True},
    "incident_description":{"label": "What happened in detail", "type": "textarea", "required": True},
    "date":              {"label": "Date of incident", "type": "date", "required": True},
    "witnesses":         {"label": "Witnesses (names & contact)", "type": "textarea", "required": False},
    "aggrieved_name":    {"label": "Your name (aggrieved person)", "type": "text", "required": True},
    "respondent_name":   {"label": "Respondent's name (the abuser)", "type": "text", "required": True},
    "relationship":      {"label": "Relationship with respondent", "type": "text", "required": True},
    "incidents":         {"label": "Incidents of violence/cruelty (with dates)", "type": "textarea", "required": True},
    "reliefs_sought":    {"label": "Reliefs you want (protection / residence / monetary / custody)", "type": "textarea", "required": True},
}


TEMPLATES = [
    {
        "id": "rental_agreement",
        "title": "Rental Agreement (11 months)",
        "category": "Property",
        "icon": "🏠",
        "fields": ["landlord_name", "tenant_name", "property_address", "rent", "deposit", "start_date"],
        "description": "Standard residential rental agreement for 11 months. Court-ready, with state-aware clauses.",
    },
    {
        "id": "rti_application",
        "title": "RTI Application",
        "category": "Government",
        "icon": "📋",
        "fields": ["public_authority", "subject", "information_sought", "applicant_name", "address"],
        "description": "Right to Information application under RTI Act 2005.",
    },
    {
        "id": "legal_notice",
        "title": "Legal Notice",
        "category": "Civil",
        "icon": "📨",
        "fields": ["recipient_name", "recipient_address", "subject", "facts", "demand", "sender_name"],
        "description": "Generic legal notice from advocate or party.",
    },
    {
        "id": "consumer_complaint",
        "title": "Consumer Complaint",
        "category": "Consumer",
        "icon": "🛒",
        "fields": ["company_name", "product", "purchase_date", "complaint_details", "relief_sought", "complainant_name", "address"],
        "description": "Complaint under Consumer Protection Act 2019. Ready for District Commission filing.",
    },
    {
        "id": "cheque_bounce_notice",
        "title": "Cheque Bounce Notice (Sec 138 NI Act)",
        "category": "Financial",
        "icon": "💰",
        "fields": ["drawer_name", "drawer_address", "cheque_number", "cheque_date", "amount", "bank", "dishonour_date", "sender_name"],
        "description": "Statutory notice under Section 138 — must be sent within 30 days of return memo.",
    },
    {
        "id": "will_simple",
        "title": "Simple Will / Testament",
        "category": "Family",
        "icon": "📜",
        "fields": ["testator_name", "address", "beneficiaries", "assets", "executor"],
        "description": "Plain English last will and testament — needs 2 witnesses on signing.",
    },
    {
        "id": "police_complaint",
        "title": "Police Complaint (General)",
        "category": "Criminal",
        "icon": "🚨",
        "fields": ["offence_type", "incident_description", "date", "witnesses", "complainant_name", "address"],
        "description": "General complaint to Station House Officer.",
    },
    {
        "id": "domestic_violence_complaint",
        "title": "Domestic Violence Application",
        "category": "Family",
        "icon": "🛡️",
        "fields": ["aggrieved_name", "respondent_name", "address", "relationship", "incidents", "reliefs_sought"],
        "description": "Application under Protection of Women from Domestic Violence Act 2005.",
    },
]


TEMPLATE_PROMPTS = {
    "rental_agreement": """Draft a legally valid 11-month RESIDENTIAL RENTAL AGREEMENT for India following standard practice and state tenancy law.

Details: {fields_json}

Include:
- Title "RENTAL AGREEMENT"
- Date, place
- Identification of Landlord (with father's name placeholder) and Tenant
- Property description (full address, area, amenities)
- Term: 11 months from start_date (so it doesn't fall under Rent Control)
- Monthly rent + payment date
- Security deposit (refundable within 30 days of vacating per TN/MH/KA Acts)
- Use clause, maintenance, utilities split
- Increment clause (typically 5-10% on renewal)
- Termination clause (1 or 2 months notice)
- Lock-in period (typically 6 months)
- Restrictions (no commercial use, no sub-letting)
- Force majeure clause
- Jurisdiction (state courts)
- Signature blocks: Landlord, Tenant, 2 Witnesses
- Stamp paper note (₹100-500 depending on state)

Output JSON ONLY:
{{
  "title": "Rental Agreement",
  "document": "FULL document text with proper headings, numbered clauses (1., 2., 3., ...), formal language, line breaks (\\n)",
  "next_steps": ["Print on ₹100 stamp paper", "Both parties sign every page", "Get 2 witnesses to sign", "Register with sub-registrar if rent + deposit > ₹50,000/month"],
  "warnings": ["State-specific stamp duty applies", "Without registration not admissible in court"]
}}
""",

    "rti_application": """Draft a Right to Information application under Section 6 of RTI Act 2005.

Details: {fields_json}

Include:
- Date, place
- To: The CPIO of the specified Public Authority
- Sub: Application under Section 6 of RTI Act 2005
- Specific, point-by-point information sought (numbered)
- Statement: "I am a citizen of India"
- Fee: ₹10 by IPO/cash (free for BPL)
- Mode of delivery preference (post / email)
- Applicant signature block with full address

Output JSON ONLY:
{{
  "title": "RTI Application",
  "document": "Full application text",
  "next_steps": ["Pay ₹10 via Indian Postal Order or cash", "Send by registered post or via rtionline.gov.in", "CPIO must reply in 30 days (48 hrs for life/liberty)"],
  "warnings": ["First Appeal in 30 days if no/incorrect reply", "Second Appeal to Information Commission in 90 days"]
}}
""",

    "legal_notice": """Draft a formal LEGAL NOTICE in standard Indian format.

Details: {fields_json}

Include:
- "LEGAL NOTICE" header
- Through advocate format OR direct from sender
- To: recipient with full address
- From: sender details
- Subject line
- Numbered factual paragraphs (with dates)
- Citation of applicable law
- Specific demand with timeline (typically 15-30 days)
- Threat of legal action if demand not met
- Signature block
- Place, date

Output JSON ONLY:
{{
  "title": "Legal Notice",
  "document": "Full notice with paragraphs",
  "next_steps": ["Send by registered post AD", "Keep proof of dispatch", "Wait for response within demand period", "File suit/complaint if no response"],
  "warnings": ["Legal notice may be required before some suits", "Use registered AD post for proof"]
}}
""",

    "consumer_complaint": """Draft a CONSUMER COMPLAINT under Section 35 of Consumer Protection Act 2019.

Details: {fields_json}

Include:
- "BEFORE THE [DISTRICT/STATE/NATIONAL] CONSUMER DISPUTES REDRESSAL COMMISSION" header
- Complaint No. (leave blank)
- Complainant details, address
- Opposite Party details, address
- Numbered factual paragraphs covering: purchase, defect/deficiency, attempts to resolve, loss caused
- Cause of action with dates
- Jurisdiction clause (territorial + pecuniary)
- Limitation clause (within 2 years)
- Prayer for relief: refund / replacement / compensation / costs / punitive damages
- Verification, signature

Output JSON ONLY:
{{
  "title": "Consumer Complaint",
  "document": "Full complaint with paragraphs",
  "next_steps": ["File via edaakhil.nic.in (online) or in person", "Pay ₹100-500 court fee based on claim", "Attach receipts, photos, correspondence"],
  "warnings": ["District Commission for claims up to ₹50L", "State for ₹50L-₹2Cr", "National for >₹2Cr"]
}}
""",

    "cheque_bounce_notice": """Draft a statutory LEGAL NOTICE under Section 138 of Negotiable Instruments Act 1881.

Details: {fields_json}

Include:
- "LEGAL NOTICE" header
- "Under Section 138 read with Section 142 of the Negotiable Instruments Act, 1881"
- Reference to my client (sender)
- To drawer with full address
- Numbered facts: cheque details (number, date, amount, bank), consideration for which issued, presentation, dishonour memo, date of dishonour
- Demand for payment of full amount within 15 days
- Notice that failure will result in criminal complaint under Sec 138
- Date, place, sender signature

Output JSON ONLY:
{{
  "title": "Section 138 NI Act Notice",
  "document": "Full statutory notice",
  "next_steps": ["Send IMMEDIATELY by registered post AD (within 30 days of dishonour)", "Wait 15 days for payment", "File complaint within 30 days of expiry of 15-day notice period before Magistrate"],
  "warnings": ["Missing any deadline = complaint dismissed", "Save dispatch proof + acknowledgment", "Keep original cheque and return memo safe"]
}}
""",

    "will_simple":  """Draft a simple LAST WILL AND TESTAMENT for an Indian testator.

Details: {fields_json}

Include:
- "LAST WILL AND TESTAMENT" header
- Declaration: This is my last will, revoking all previous wills/codicils, made of sound mind, no coercion
- Identification of testator with father's name + age placeholder
- Appointment of Executor
- Disposition of each asset with specific beneficiary (numbered)
- Residuary clause
- Funeral wishes (optional)
- Date, place
- Testator's signature placeholder
- Two witnesses' signature placeholders ("Witness 1, Witness 2 — please add names, addresses, occupations")

Output JSON ONLY:
{{
  "title": "Last Will and Testament",
  "document": "Full will text",
  "next_steps": ["Sign in presence of 2 witnesses who must also sign", "Witnesses must NOT be beneficiaries", "Registration optional but recommended (₹500-1000 fee)", "Keep original safe; tell executor where it is"],
  "warnings": ["Witnesses cannot inherit", "Probate may be required in Mumbai/Chennai/Kolkata jurisdiction", "Hindu Succession Act applies for intestate Hindus"]
}}
""",

    "police_complaint": """Draft a formal POLICE COMPLAINT addressed to the Station House Officer.

Details: {fields_json}

Include:
- "To, The Station House Officer, [nearest] Police Station"
- Date, place
- Subject: Complaint regarding [offence_type]
- Salutation
- Numbered paragraphs: who I am, what happened, when, where, who is involved, evidence available
- Witnesses
- Section reference (e.g. IPC 420 / BNS 318(4) for cheating)
- Prayer for FIR registration and investigation
- Closing: Yours faithfully, complainant_name, address, phone

Output JSON ONLY:
{{
  "title": "Police Complaint",
  "document": "Full letter",
  "next_steps": ["Print 2 copies", "Submit at PS — get diary number on acknowledged copy", "If refused, send to SP, then approach Magistrate u/s 156(3) CrPC / 175(3) BNSS"],
  "warnings": ["False complaint is offence under IPC 211 / BNS 248", "Attach ID proof", "Keep all evidence safely"]
}}
""",

    "domestic_violence_complaint": """Draft an APPLICATION under Section 12 of Protection of Women from Domestic Violence Act 2005.

Details: {fields_json}

Include:
- "BEFORE THE COURT OF [JUDICIAL] MAGISTRATE [FIRST CLASS]" header
- Application under Sec 12 DV Act 2005
- Aggrieved person details, address
- Respondent details, address
- Relationship description (domestic relationship)
- Numbered paragraphs detailing incidents of physical/sexual/verbal/emotional/economic abuse with dates
- Domestic Incident Report reference (if filed)
- Specific reliefs sought: Protection Order (Sec 18), Residence Order (Sec 19), Monetary Relief (Sec 20), Custody Order (Sec 21), Compensation Order (Sec 22)
- Prayer, verification, signature

Output JSON ONLY:
{{
  "title": "DV Act Application",
  "document": "Full application",
  "next_steps": ["File before Magistrate of place where aggrieved resides / works", "Approach Protection Officer for DIR", "Court may grant interim reliefs ex-parte"],
  "warnings": ["Civil reliefs — no automatic arrest", "Parallel FIR under IPC 498A / BNS 85 possible", "DIR strengthens application"]
}}
"""
}


class GenerateRequest(BaseModel):
    template_id: str = Field(..., max_length=64)
    fields: dict = Field(default_factory=dict)
    state: str = Field(default="Tamil Nadu", max_length=64)


class GenerateResponse(BaseModel):
    status: str
    title: str | None = None
    document: str | None = None
    next_steps: list[str] = []
    warnings: list[str] = []
    message: str | None = None


@router.get("/field-defs")
def get_field_defs():
    """Labels/types for every supported field."""
    return FIELD_DEFS


@router.post("/generate", response_model=GenerateResponse)
@limiter.limit("15/minute")
async def generate_document(request: Request, req: GenerateRequest):
    template = next((t for t in TEMPLATES if t["id"] == req.template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{req.template_id}' not found")

    prompt_template = TEMPLATE_PROMPTS.get(req.template_id)
    if not prompt_template:
        raise HTTPException(status_code=501, detail="Generator not configured for this template")

    # Build context with field values
    import json as _json
    fields_json = _json.dumps(req.fields, indent=2, ensure_ascii=False)
    prompt = prompt_template.format(fields_json=fields_json) + f"\n\nState context: {req.state}\n"

    fallback = {
        "title": template["title"],
        "document": "Document generation failed. Please try again.",
        "next_steps": [],
        "warnings": [],
    }

    try:
        data = await generate_json(prompt, fallback, max_tokens=6144)
    except GeminiError as exc:
        log.error("template_gen_failed", template=req.template_id, error=str(exc))
        return GenerateResponse(status="error", message=str(exc), title=template["title"])

    return GenerateResponse(
        status="success",
        title=str(data.get("title", template["title"])),
        document=str(data.get("document", "")).strip(),
        next_steps=[str(x) for x in (data.get("next_steps") or [])],
        warnings=[str(x) for x in (data.get("warnings") or [])],
    )


@router.get("/")
def list_templates(category: str | None = None):
    if category:
        return [t for t in TEMPLATES if t["category"].lower() == category.lower()]
    return TEMPLATES


@router.get("/{template_id}")
def get_template(template_id: str):
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    return {"error": "Template not found"}, 404


@router.get("/categories/list")
def list_categories():
    return sorted({t["category"] for t in TEMPLATES})
