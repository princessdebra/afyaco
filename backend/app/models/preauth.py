import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class PreAuthStatus(str, enum.Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    INFO_REQUESTED = "info_requested"
    APPROVED = "approved"
    DENIED = "denied"


class PreAuthRequest(IdMixin, TimestampMixin, Base):
    """Orchestration state for a pre-authorisation (brief §8 "Authorisation
    orchestration": requirement check, request assembly, attachments,
    submission, information requests, decision, status, audit).

    This table owns the *workflow* — queueing, attachments, status transitions,
    member/clinician communication. The actual decision always comes from the
    tenant's adapter (Minet's existing rules engine, brief §2) via
    `external_request_id`; we do not implement a second rules engine here.
    """

    __tablename__ = "preauth_requests"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id"), index=True)
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinical_recommendations.id"), nullable=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True
    )

    service_reference: Mapped[str] = mapped_column(String(255))
    status: Mapped[PreAuthStatus] = mapped_column(Enum(PreAuthStatus, name="preauth_status"), default=PreAuthStatus.PENDING)
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    conditions: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    reasons: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    approved_amount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    validity: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Set once the actual adapter submission is wired up (deferred — needs the
    # tenant's real pre-auth API per brief §2/§4).
    external_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
