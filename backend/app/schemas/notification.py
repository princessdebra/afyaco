import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.notification import NotificationType


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: NotificationType
    title: str
    body: str
    link: str | None
    read_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class UnreadCountOut(BaseModel):
    count: int
