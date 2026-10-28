import uuid

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class AuditLog(IdMixin, TimestampMixin, Base):
    """Brief §15: audit clinical-record access, prescription/order creation,
    authorisation and claims changes, FAWE submissions, document downloads and
    configuration changes. Append-only — services write to this, nothing
    updates or deletes a row.
    """

    __tablename__ = "audit_logs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(128))  # e.g. "appointment.booked", "clinical_note.read"
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64))
    context: Mapped[dict] = mapped_column(JSON, default=dict)
