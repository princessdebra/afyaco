import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.claim import ClaimStatus


class ClaimCreate(BaseModel):
    member_id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    preauth_id: uuid.UUID | None = None
    lines: list[dict]


class ClaimOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    status: ClaimStatus
    lines: list[dict]
    external_claim_id: str | None
    submitted_at: datetime | None
    decided_at: datetime | None

    class Config:
        from_attributes = True
