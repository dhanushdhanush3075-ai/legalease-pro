import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, JSON, Boolean
from sqlalchemy.orm import relationship
from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    phone = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    state = Column(String, default="Tamil Nadu")
    is_phone_verified = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_login_at = Column(DateTime, default=datetime.utcnow)


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id = Column(String, primary_key=True, default=_uuid)
    target = Column(String, index=True)  # phone or email
    code_hash = Column(String, nullable=False)
    purpose = Column(String, default="login")  # login | signup
    attempts = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=True)
    device_id = Column(String, index=True, nullable=True)
    title = Column(String, default="New chat")
    state = Column(String, default="Tamil Nadu")
    language = Column(String, default="english")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role = Column(String, nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=list)
    alerts = Column(JSON, default=list)
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    session = relationship("Session", back_populates="messages")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=True)
    device_id = Column(String, index=True, nullable=True)
    offence_type = Column(String)
    state = Column(String)
    description = Column(Text)
    incident_date = Column(String)
    witnesses = Column(Text)
    victim_name = Column(String)
    victim_address = Column(Text)
    fir_text = Column(Text)
    ipc_sections = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
