import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
import base64
import json

from app.core.config import get_settings

settings = get_settings()


# ---------- OTP ----------

def generate_otp(length: int = 6) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def hash_otp(code: str) -> str:
    return hashlib.sha256((settings.JWT_SECRET + ":" + code).encode("utf-8")).hexdigest()


def verify_otp_hash(code: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_otp(code), hashed)


# ---------- JWT (HS256, no extra deps) ----------

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = 4 - (len(data) % 4)
    return base64.urlsafe_b64decode(data + ("=" * pad))


def issue_jwt(user_id: str, extra: dict[str, Any] | None = None) -> str:
    now = int(time.time())
    exp = now + settings.JWT_EXPIRE_DAYS * 86400
    header = {"alg": settings.JWT_ALG, "typ": "JWT"}
    payload = {"sub": user_id, "iat": now, "exp": exp}
    if extra:
        payload.update(extra)
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(settings.JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url(sig)}"


def decode_jwt(token: str) -> dict[str, Any] | None:
    try:
        h, p, s = token.split(".")
        signing_input = f"{h}.{p}".encode()
        expected_sig = hmac.new(settings.JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url(expected_sig), s):
            return None
        payload = json.loads(_b64url_decode(p))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
