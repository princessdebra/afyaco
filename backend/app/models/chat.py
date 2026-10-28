import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class ChatSenderRole(str, enum.Enum):
    MEMBER = "member"
    CLINICIAN = "clinician"


class ChatMessage(IdMixin, TimestampMixin, Base):
    """A persisted chat-consultation message (brief §13 — the member/clinician
    text channel). Real-time delivery is a WebSocket broadcast
    (app/services/chat_hub.py); this table is the durable record and the
    history backfill when either side opens the thread.
    """

    __tablename__ = "chat_messages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consultations.id"), index=True
    )
    sender_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    sender_role: Mapped[ChatSenderRole] = mapped_column(Enum(ChatSenderRole, name="chat_sender_role"))
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
