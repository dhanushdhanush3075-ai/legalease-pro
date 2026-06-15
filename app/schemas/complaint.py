from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class ComplaintData(BaseModel):
    offence_type: str = Field(..., min_length=2, max_length=128)
    state: str = Field(..., max_length=64)
    description: str = Field(..., min_length=10, max_length=4000)
    date: str = Field(..., max_length=32)
    witnesses: str = Field(default="", max_length=2000)
    name: str = Field(..., min_length=2, max_length=128)
    address: str = Field(..., min_length=5, max_length=512)
    device_id: str | None = Field(default=None, max_length=128)


class ComplaintResponse(BaseModel):
    fir_text: str
    ipc_sections: str
    alerts: list[str] = []


class ComplaintApiResponse(BaseModel):
    status: Literal["success", "error"]
    complaint_id: str | None = None
    response: ComplaintResponse | None = None
    message: str | None = None


class ComplaintOut(BaseModel):
    id: str
    offence_type: str
    state: str
    fir_text: str
    ipc_sections: str
    created_at: datetime

    class Config:
        from_attributes = True
