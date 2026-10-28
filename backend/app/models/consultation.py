import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class ConsultationStatus(str, enum.Enum):
    PENDING_CONSENT = "pending_consent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"


class Consultation(IdMixin, TimestampMixin, Base):
    """Brief §13 safety requirements: identity/location/clinician verification
    and consent must be recorded for every teleconsultation. Does not wire an
    actual video provider — `session_ref` is where that provider's session id
    would go once a media provider is selected (integration work, deferred).
    """

    __tablename__ = "consultations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), unique=True, index=True
    )
    status: Mapped[ConsultationStatus] = mapped_column(
        Enum(ConsultationStatus, name="consultation_status"), default=ConsultationStatus.PENDING_CONSENT
    )

    consent_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    identity_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    location_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    clinician_identity_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    session_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clinical_note: Mapped[str | None] = mapped_column(Text, nullable=True)  # access-restricted, audited on read


class RecommendationKind(str, enum.Enum):
    PRESCRIPTION = "prescription"
    LAB_TEST = "lab_test"
    REFERRAL = "referral"
    IMAGING = "imaging"
    ADMISSION = "admission"
    FOLLOW_UP = "follow_up"


class ClinicalRecommendation(IdMixin, TimestampMixin, Base):
    """Structured output of a consultation (brief §6 step 6). `details` holds the
    kind-specific structured payload (medicine + dosage, test codes, referral
    target, etc.) so each kind doesn't need its own table yet.
    """

    __tablename__ = "clinical_recommendations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    # Nullable: most recommendations come out of a consultation (brief §6 step
    # 6), but a member can also self-request a lab test directly (no clinician
    # visit) — that order has no consultation to hang off.
    consultation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consultations.id"), index=True, nullable=True
    )
    # Denormalized for direct "my prescriptions"/"my lab tests" queries —
    # otherwise every list view needs a consultation -> appointment -> member
    # join for something that's 1:1 with the recommendation in practice.
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id"), index=True)
    kind: Mapped[RecommendationKind] = mapped_column(Enum(RecommendationKind, name="recommendation_kind"))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    requires_preauth: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # set once checked (brief §7)
