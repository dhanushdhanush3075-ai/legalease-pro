from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DBSession
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.database import get_db
from app.db.models import Complaint
from app.schemas.complaint import ComplaintData, ComplaintApiResponse, ComplaintResponse
from app.services.gemini import generate_json, COMPLAINT_SYSTEM_PROMPT, GeminiError

router = APIRouter(prefix="/api/legal", tags=["complaint"])
log = get_logger(__name__)


@router.post("/complaint", response_model=ComplaintApiResponse)
@limiter.limit("10/minute")
async def generate_fir(
    request: Request,
    req: ComplaintData,
    db: DBSession = Depends(get_db),
):
    prompt = COMPLAINT_SYSTEM_PROMPT.format(
        offence_type=req.offence_type,
        state=req.state,
        description=req.description,
        date=req.date,
        witnesses=req.witnesses or "None mentioned",
        name=req.name,
        address=req.address,
    )
    fallback = {
        "fir_text": "Unable to draft right now. Please try again.",
        "ipc_sections": "",
        "alerts": [],
    }

    try:
        data = await generate_json(prompt, fallback, max_tokens=6144)
    except GeminiError as exc:
        log.error("complaint_failed", error=str(exc))
        return ComplaintApiResponse(
            status="error",
            message="AI service is temporarily unavailable. Please try again.",
        )

    resp = ComplaintResponse(
        fir_text=str(data.get("fir_text", "")).strip() or fallback["fir_text"],
        ipc_sections=str(data.get("ipc_sections", "")).strip(),
        alerts=[str(a) for a in (data.get("alerts") or [])],
    )

    row = Complaint(
        device_id=req.device_id,
        offence_type=req.offence_type,
        state=req.state,
        description=req.description,
        incident_date=req.date,
        witnesses=req.witnesses,
        victim_name=req.name,
        victim_address=req.address,
        fir_text=resp.fir_text,
        ipc_sections=resp.ipc_sections,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log.info("complaint_ok", complaint_id=row.id, state=req.state)

    return ComplaintApiResponse(
        status="success",
        complaint_id=row.id,
        response=resp,
    )
