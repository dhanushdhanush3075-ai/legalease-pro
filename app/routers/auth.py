from datetime import datetime, timedelta
import re
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.core.security import (
    generate_otp, hash_otp, verify_otp_hash, issue_jwt, decode_jwt,
)
from app.db.database import get_db
from app.db.models import User, OtpCode

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = get_logger(__name__)
settings = get_settings()

PHONE_RE = re.compile(r"^\d{10}$")


# ---------- Schemas ----------

class SendOtpReq(BaseModel):
    phone: str = Field(..., min_length=10, max_length=10)
    purpose: str = "login"  # login | signup
    name: str | None = None
    state: str | None = None


class VerifyOtpReq(BaseModel):
    phone: str = Field(..., min_length=10, max_length=10)
    code: str = Field(..., min_length=6, max_length=6)


class UserOut(BaseModel):
    id: str
    phone: str | None
    email: str | None
    name: str | None
    state: str
    is_phone_verified: bool

    class Config:
        from_attributes = True


class AuthTokenResp(BaseModel):
    status: str = "success"
    token: str
    user: UserOut


class SendOtpResp(BaseModel):
    status: str = "success"
    message: str
    expires_in: int
    dev_code: str | None = None  # only present in dev mode


# ---------- Dependencies ----------

def get_current_user(
    authorization: str | None = Header(default=None),
    db: DBSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_optional_user(
    authorization: str | None = Header(default=None),
    db: DBSession = Depends(get_db),
) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    payload = decode_jwt(authorization.split(" ", 1)[1].strip())
    if not payload:
        return None
    return db.get(User, payload["sub"])


# ---------- Endpoints ----------

@router.post("/send-otp", response_model=SendOtpResp)
@limiter.limit("5/minute")
async def send_otp(request: Request, req: SendOtpReq, db: DBSession = Depends(get_db)):
    if not PHONE_RE.match(req.phone):
        raise HTTPException(status_code=400, detail="Phone must be 10 digits")

    # Invalidate previous OTPs for this target
    db.query(OtpCode).filter(OtpCode.target == req.phone, OtpCode.consumed_at.is_(None)).update(
        {OtpCode.consumed_at: datetime.utcnow()}
    )

    code = generate_otp(6)
    row = OtpCode(
        target=req.phone,
        code_hash=hash_otp(code),
        purpose=req.purpose,
        expires_at=datetime.utcnow() + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    db.add(row)

    if req.purpose == "signup":
        existing = db.query(User).filter(User.phone == req.phone).first()
        if not existing:
            db.add(User(
                phone=req.phone,
                name=req.name or None,
                state=req.state or "Tamil Nadu",
            ))

    db.commit()
    log.info("otp_sent", phone=req.phone, purpose=req.purpose, dev_code=code if settings.OTP_DEV_MODE else "***")

    # In production, this is where you'd call Twilio / Fast2SMS / MSG91.
    return SendOtpResp(
        message=f"OTP sent to +91 {req.phone}",
        expires_in=settings.OTP_TTL_SECONDS,
        dev_code=code if settings.OTP_DEV_MODE else None,
    )


@router.post("/verify-otp", response_model=AuthTokenResp)
@limiter.limit("10/minute")
async def verify_otp(request: Request, req: VerifyOtpReq, db: DBSession = Depends(get_db)):
    if not PHONE_RE.match(req.phone):
        raise HTTPException(status_code=400, detail="Phone must be 10 digits")
    if not re.fullmatch(r"\d{6}", req.code):
        raise HTTPException(status_code=400, detail="OTP must be 6 digits")

    otp = (
        db.query(OtpCode)
        .filter(
            OtpCode.target == req.phone,
            OtpCode.consumed_at.is_(None),
            OtpCode.expires_at > datetime.utcnow(),
        )
        .order_by(OtpCode.created_at.desc())
        .first()
    )
    if not otp:
        raise HTTPException(status_code=400, detail="No active OTP. Please request a new one.")

    if otp.attempts >= 5:
        otp.consumed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts. Please request a new OTP.")

    if not verify_otp_hash(req.code, otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail=f"Wrong OTP. {5 - otp.attempts} attempts left.")

    otp.consumed_at = datetime.utcnow()

    user = db.query(User).filter(User.phone == req.phone).first()
    if not user:
        user = User(phone=req.phone, is_phone_verified=True)
        db.add(user)
    user.is_phone_verified = True
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    token = issue_jwt(user.id, {"phone": user.phone})
    log.info("user_login", user_id=user.id, phone=user.phone)
    return AuthTokenResp(token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    # Stateless JWT — client just drops the token. Endpoint exists for symmetry.
    log.info("user_logout", user_id=user.id)
    return {"status": "success"}
