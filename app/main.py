from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import __version__
from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.logging import setup_logging, get_logger
from app.db.database import init_db
from app.routers import chat, complaint, history, templates, auth, laws, analyse, courts, calculators, lawyers, tracker, news, core

setup_logging()
log = get_logger("legalease")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("startup_complete", env=settings.APP_ENV, model=settings.GEMINI_MODEL)
    yield
    log.info("shutdown")


app = FastAPI(
    title="LegalEase Pro API",
    description="AI-powered Indian legal assistance backend",
    version=__version__,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def access_log(request: Request, call_next):
    response = await call_next(request)
    log.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        client=request.client.host if request.client else None,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exc(request: Request, exc: Exception):
    log.error("unhandled", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"},
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": __version__,
        "model": settings.GEMINI_MODEL,
        "env": settings.APP_ENV,
    }


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(complaint.router)
app.include_router(analyse.router)
app.include_router(history.router)
app.include_router(templates.router)
app.include_router(laws.router)
app.include_router(courts.router)
app.include_router(calculators.router)
app.include_router(lawyers.router)
app.include_router(tracker.router)
app.include_router(news.router)
app.include_router(core.router)


# --- Static frontend (PWA) ---
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    @app.get("/")
    def fallback_root():
        return {"message": "LegalEase Pro API", "docs": "/docs"}
