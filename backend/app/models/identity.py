"""Xenova Identity Assurance (XIA): hardware-free facial verification bound to
a hospital-initiated encounter. Identity verification, liveness, location
corroboration and insurance eligibility are tracked as separate outcomes —
never collapsed into one boolean (see module docstrings below for why).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    PENDING_DELETION = "pending_deletion"


class BiometricEnrollment(IdMixin, TimestampMixin, Base):
    """One active enrollment per member. Holds only an opaque provider-managed
    reference — never a raw image or a reversible template (brief §4.5). The
    mock provider (app/biometrics/mock.py) stores a SHA-256 digest in place of
    a real template; that is explicitly NOT biometric protection and must not
    be used in production (see app/biometrics/README or module docstring).
    """

    __tablename__ = "biometric_enrollments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id"), index=True)
    provider_key: Mapped[str] = mapped_column(String(64))  # e.g. "mock-v1"
    # Opaque, provider-defined. Unbounded: the mock provider's digest is tiny
    # but a real ArcFace embedding base64-encodes to ~2.7KB — sizing this as
    # a short VARCHAR caused a real 500 in testing (StringDataRightTruncation).
    template_ref: Mapped[str] = mapped_column(Text)
    template_version: Mapped[str] = mapped_column(String(64))  # widened for headroom after the template_ref incident above
    status: Mapped[EnrollmentStatus] = mapped_column(Enum(EnrollmentStatus, name="enrollment_status"), default=EnrollmentStatus.ACTIVE)
    enrollment_method: Mapped[str] = mapped_column(String(64), default="self_capture")
    consent_ref: Mapped[str] = mapped_column(String(255))  # pointer to the consent/legal-basis record
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChallengeStatus(str, enum.Enum):
    PENDING = "pending"
    CONSUMED = "consumed"
    REVOKED = "revoked"
    EXPIRED = "expired"


class VerificationChallenge(IdMixin, TimestampMixin, Base):
    """Short-lived, single-use, facility- and encounter-bound challenge (brief
    §6.3). Only a SHA-256 hash of the token is stored — the plaintext token is
    returned once at creation and never persisted, so a DB read can't leak it.
    """

    __tablename__ = "verification_challenges"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hospital_encounters.id"), index=True)
    facility_provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("providers.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # sha256 hex digest
    status: Mapped[ChallengeStatus] = mapped_column(Enum(ChallengeStatus, name="challenge_status"), default=ChallengeStatus.PENDING)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChallengeAction(str, enum.Enum):
    """Instruction shown to the member during challenge-response liveness
    (brief: defeats a static photo/pre-recorded loop, which cannot respond to
    an action chosen at random, after the fact)."""

    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    NOD = "nod"


class LivenessChallengePurpose(str, enum.Enum):
    ENROLLMENT = "enrollment"
    VERIFICATION = "verification"


class LivenessChallengeStatus(str, enum.Enum):
    PENDING = "pending"
    CONSUMED = "consumed"
    EXPIRED = "expired"


class LivenessChallenge(IdMixin, TimestampMixin, Base):
    """A randomly-chosen action the member must perform on camera, issued
    fresh per enrollment/verification attempt and single-use. The server
    measures head pose from the submitted frames itself (see
    services/liveness_challenge.py) — the action to perform is the only thing
    the client is told; nothing about whether the response was correct is
    ever decided client-side.
    """

    __tablename__ = "liveness_challenges"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id"), nullable=True, index=True)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("hospital_encounters.id"), nullable=True, index=True)
    purpose: Mapped[LivenessChallengePurpose] = mapped_column(Enum(LivenessChallengePurpose, name="liveness_challenge_purpose"))
    action: Mapped[ChallengeAction] = mapped_column(Enum(ChallengeAction, name="challenge_action"))
    status: Mapped[LivenessChallengeStatus] = mapped_column(Enum(LivenessChallengeStatus, name="liveness_challenge_status"), default=LivenessChallengeStatus.PENDING)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChallengeResponseOutcome(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class EncounterStatus(str, enum.Enum):
    CREATED = "created"
    CHALLENGE_ISSUED = "challenge_issued"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IdentityStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    RETRY_REQUIRED = "retry_required"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class EligibilityStatus(str, enum.Enum):
    NOT_CHECKED = "not_checked"
    CONFIRMED = "confirmed"
    PENDING = "pending"
    UNAVAILABLE = "unavailable"
    NOT_ELIGIBLE = "not_eligible"


class HospitalEncounter(IdMixin, TimestampMixin, Base):
    """A facility-initiated visit (brief §6). Deliberately separate from
    Appointment — an encounter can exist for a walk-in with no prior booking,
    though `appointment_id` links the two when one exists.
    """

    __tablename__ = "hospital_encounters"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id"), index=True)
    facility_provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("providers.id"), index=True)
    initiated_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=True)

    status: Mapped[EncounterStatus] = mapped_column(Enum(EncounterStatus, name="encounter_status"), default=EncounterStatus.CREATED)
    identity_status: Mapped[IdentityStatus] = mapped_column(Enum(IdentityStatus, name="identity_status"), default=IdentityStatus.NOT_STARTED)
    eligibility_status: Mapped[EligibilityStatus] = mapped_column(Enum(EligibilityStatus, name="eligibility_status"), default=EligibilityStatus.NOT_CHECKED)
    preauth_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("preauth_requests.id"), nullable=True)
    verification_policy_version: Mapped[str] = mapped_column(String(32), default="xia-policy-v1")


class LivenessOutcome(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class QualityOutcome(str, enum.Enum):
    ACCEPTABLE = "acceptable"
    REJECTED = "rejected"


class MatchOutcome(str, enum.Enum):
    MATCH = "match"
    NO_MATCH = "no_match"
    NOT_ENROLLED = "not_enrolled"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


class LocationOutcome(str, enum.Enum):
    ACCEPTED = "accepted"
    OUT_OF_RANGE = "out_of_range"
    STALE = "stale"
    IMPLAUSIBLE = "implausible"
    UNAVAILABLE = "unavailable"


class OverallOutcome(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class IdentityVerificationAttempt(IdMixin, TimestampMixin, Base):
    """One verification attempt. Every signal is recorded independently (brief
    §5, §7.3) — `overall_outcome` is a policy decision computed from the
    others, not a separate ground truth the caller can set directly.
    """

    __tablename__ = "identity_verification_attempts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id"), index=True)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hospital_encounters.id"), index=True)
    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("biometric_enrollments.id"), nullable=True)
    # Nullable: the hospital-facility QR challenge is consumed (and audited)
    # separately in start_verification() — by the time this row is written,
    # only the liveness_challenge_id below is in scope.
    challenge_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("verification_challenges.id"), nullable=True)
    liveness_challenge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("liveness_challenges.id"))

    quality_outcome: Mapped[QualityOutcome] = mapped_column(Enum(QualityOutcome, name="quality_outcome"))
    liveness_outcome: Mapped[LivenessOutcome] = mapped_column(Enum(LivenessOutcome, name="liveness_outcome"))
    challenge_response_outcome: Mapped[ChallengeResponseOutcome] = mapped_column(
        Enum(ChallengeResponseOutcome, name="challenge_response_outcome"), default=ChallengeResponseOutcome.UNAVAILABLE
    )
    match_outcome: Mapped[MatchOutcome] = mapped_column(Enum(MatchOutcome, name="match_outcome"))
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_outcome: Mapped[LocationOutcome] = mapped_column(Enum(LocationOutcome, name="location_outcome"))
    location_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_outcome: Mapped[OverallOutcome] = mapped_column(Enum(OverallOutcome, name="overall_outcome"))

    provider_key: Mapped[str] = mapped_column(String(64))
    risk_policy_version: Mapped[str] = mapped_column(String(32), default="xia-policy-v1")
