import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.appointment import AppointmentMode, AppointmentStatus


class AppointmentCreate(BaseModel):
    member_id: uuid.UUID
    provider_id: uuid.UUID
    mode: AppointmentMode
    scheduled_at: datetime
    reason: str | None = None
    idempotency_key: str


class AppointmentOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    provider_id: uuid.UUID
    mode: AppointmentMode
    scheduled_at: datetime
    status: AppointmentStatus
    reason: str | None
    cover_confirmed: bool
    cover_check_source: str | None

    class Config:
        from_attributes = True
