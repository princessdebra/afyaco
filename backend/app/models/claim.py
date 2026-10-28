import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class ClaimStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_ACTION = "needs_action"
    PAID = "paid"


class Claim(IdMixin, TimestampMixin, Base):
    """Brief §8 "Claims orchestration": claim/line creation, encounter and
    authorisation linkage, evidence, status, exceptions, communication, payment
    reference. Submission to the tenant's claims API and to the existing FAWE
    (brief §12) is deferred — this table owns local workflow state only.
    """

    __tablename__ = "claims"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id"), index=True)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True
    )
    preauth_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("preauth_requests.id"), nullable=True
    )

    lines: Mapped[list] = mapped_column(JSON, default=list)  # [{service, amount, covered, member_amount}, ...]
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus, name="claim_status"), default=ClaimStatus.DRAFT)
    evidence: Mapped[list] = mapped_column(JSON, default=list)

    external_claim_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Populated once the real FAWE integration (brief §12) is wired up.
    fawe_assessment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fawe_risk_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
