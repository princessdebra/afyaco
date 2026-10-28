import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class NotificationType(str, enum.Enum):
    CHAT_MESSAGE = "chat_message"
    APPOINTMENT_REMINDER = "appointment_reminder"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    APPOINTMENT_DECLINED = "appointment_declined"
    INCOMING_CALL = "incoming_call"


class Notification(IdMixin, TimestampMixin, Base):
    """A per-user notification — chat messages and appointment reminders feed
    into this same inbox (bell dropdown) rather than each having its own ad
    hoc popup mechanism. Delivered live over notification_hub's WebSocket
    when the recipient is connected; always readable via REST regardless.
    """

    __tablename__ = "notifications"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    # Frontend route to open when the notification is clicked, e.g.
    # /portal/chat/<appointment_id> — intentionally opaque to the backend.
    link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
