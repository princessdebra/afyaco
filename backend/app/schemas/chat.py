import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.chat import ChatSenderRole


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    sender_role: ChatSenderRole
    body: str
    created_at: datetime
    read_at: datetime | None

    class Config:
        from_attributes = True
