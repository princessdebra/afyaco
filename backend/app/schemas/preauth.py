import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.preauth import PreAuthStatus


class PreAuthCreate(BaseModel):
    member_id: uuid.UUID
    service_reference: str
    service_code: str
    recommendation_id: uuid.UUID | None = None
    appointment_id: uuid.UUID | None = None
    attachments: list[dict] = []


class PreAuthOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    service_reference: str
    status: PreAuthStatus
    external_request_id: str | None
    conditions: str | None
    reasons: str | None
    submitted_at: datetime | None
    decided_at: datetime | None

    class Config:
        from_attributes = True
