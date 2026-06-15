# Backward-compat shim — the real app lives in app/main.py
# Run with: uvicorn app.main:app --reload --port 8001
from app.main import app  # noqa: F401
