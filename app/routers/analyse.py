from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.services.gemini import generate_json, generate_json_with_image, DOC_ANALYSE_PROMPT, GeminiError

router = APIRouter(prefix="/api/legal", tags=["analyse"])
log = get_logger(__name__)

ALLOWED_MIME = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/analyse-doc")
@limiter.limit("10/minute")
async def analyse_document(
    request: Request,
    language: str = Form("english"),
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
):
    if not text and not file:
        raise HTTPException(status_code=400, detail="Provide either 'text' or 'file'")

    fallback = {
        "doc_type": "Unknown",
        "title": "Could not parse document",
        "what_it_is": "The document could not be analysed. Please paste text or upload a clearer image.",
        "key_points": [],
        "sections_cited": [],
        "deadline": "None",
        "what_to_do": "Try uploading a higher resolution image, or paste the document text directly.",
        "risk_level": "low",
        "alerts": [],
    }

    prompt = DOC_ANALYSE_PROMPT.format(language=language)

    try:
        if file:
            if file.content_type not in ALLOWED_MIME:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
            data = await file.read()
            if len(data) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large (max 10MB)")
            log.info("analyse_doc_file", filename=file.filename, size=len(data), mime=file.content_type)
            result = await generate_json_with_image(prompt, data, file.content_type, fallback)
        else:
            text_prompt = prompt + "\n\nDocument text:\n" + (text or "")
            log.info("analyse_doc_text", chars=len(text or ""))
            result = await generate_json(text_prompt, fallback, max_tokens=4096)
        return {"status": "success", "response": result}
    except GeminiError as exc:
        return {"status": "error", "message": str(exc), "response": fallback}
    except HTTPException:
        raise
    except Exception as exc:
        log.error("analyse_doc_failed", error=str(exc))
        return {"status": "error", "message": "Analysis failed", "response": fallback}
