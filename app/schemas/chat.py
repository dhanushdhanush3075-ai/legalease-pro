from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class Citation(BaseModel):
    ref: str = ""
    name: str = ""
    meta: str = ""


class Alert(BaseModel):
    type: str = "action"
    text: str = ""


class LegalQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    state: str = Field(default="Tamil Nadu", max_length=64)
    language: str = Field(default="english", max_length=32)
    session_id: str | None = None
    device_id: str | None = Field(default=None, max_length=128)


class ChatResponse(BaseModel):
    text: str
    citations: list[Citation] = []
    alerts: list[Alert] = []


class ChatApiResponse(BaseModel):
    status: Literal["success", "error"]
    session_id: str | None = None
    message_id: str | None = None
    response: ChatResponse | None = None
    message: str | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: list[Citation] = []
    alerts: list[Alert] = []
    created_at: datetime

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: str
    title: str
    state: str
    language: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
