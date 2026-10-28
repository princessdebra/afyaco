import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.appointment import AppointmentMode
from app.models.consultation import ConsultationStatus


class ConsultationOut(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    status: ConsultationStatus
    session_ref: str | None
    started_at: datetime | None
    ended_at: datetime | None
    identity_verified: bool
    location_confirmed: bool

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    consultation_id: uuid.UUID
    appointment_id: uuid.UUID
    counterpart_name: str
    mode: AppointmentMode
    status: ConsultationStatus
    last_message: str | None
    last_message_at: datetime
    unread_count: int
