import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.biometrics.base import BiometricVerificationProvider, LivenessDecision, QualityDecision
from app.core.config import settings
from app.models.identity import BiometricEnrollment, ChallengeResponseOutcome, EnrollmentStatus, LivenessChallengePurpose
from app.services import audit, liveness_challenge
from app.services.identity_errors import IdentityError


async def enroll_member(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    provider: BiometricVerificationProvider,
    member_id: uuid.UUID,
    liveness_challenge_id: uuid.UUID,
    frames: list[bytes],
    consent_ref: str,
) -> BiometricEnrollment:
    """Brief §4.4: quality + liveness must pass before a reference is
    created. Brief §4.5: a member cannot silently overwrite an active
    enrollment by submitting a new selfie — an active enrollment must be
    explicitly revoked first (see `revoke_enrollment`).

    `frames` is a burst captured while the member performed the action named
    by `liveness_challenge_id` (see services/liveness_challenge.py) — frame
    [0] is the frontal "baseline" shot used for the actual enrollment
    reference; later frames exist only to measure the head-turn response.
    """
    existing = (
        db.query(BiometricEnrollment)
        .filter(
            BiometricEnrollment.tenant_id == tenant_id,
            BiometricEnrollment.member_id == member_id,
            BiometricEnrollment.status == EnrollmentStatus.ACTIVE,
        )
        .first()
    )
    if existing is not None:
        raise IdentityError(
            "Member already has an active biometric enrollment. Revoke it before re-enrolling.",
            status_code=409,
        )

    _challenge, response_outcome, baseline_frame, response_detail = await liveness_challenge.verify_response(
        db,
        tenant_id=tenant_id,
        provider=provider,
        challenge_id=liveness_challenge_id,
        purpose=LivenessChallengePurpose.ENROLLMENT,
        frames=frames,
    )
    if response_outcome != ChallengeResponseOutcome.PASSED:
        raise IdentityError(
            response_detail,
            status_code=422,
        )

    quality = await provider.assess_capture_quality(baseline_frame)
    if quality.decision == QualityDecision.REJECTED:
        raise IdentityError(f"Capture quality rejected: {quality.reason}", status_code=422)

    liveness = await provider.perform_liveness_check(baseline_frame)
    liveness_passed = liveness.decision == LivenessDecision.PASSED
    if not liveness_passed and settings.xia_passive_liveness_enforcement == "hard":
        raise IdentityError(f"Liveness check did not pass: {liveness.reason}", status_code=422)

    reference = await provider.create_enrollment_reference(baseline_frame)

    enrollment = BiometricEnrollment(
        tenant_id=tenant_id,
        member_id=member_id,
        provider_key=provider.key,
        template_ref=reference.template_ref,
        template_version=reference.template_version,
        status=EnrollmentStatus.ACTIVE,
        consent_ref=consent_ref,
    )
    db.add(enrollment)
    db.flush()

    audit.record(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="biometric_enrollment.created",
        resource_type="biometric_enrollment",
        resource_id=str(enrollment.id),
        context={
            "provider_key": provider.key,
            "challenge_response": response_outcome.value,
            "passive_liveness_passed": liveness_passed,
            "passive_liveness_enforcement": settings.xia_passive_liveness_enforcement,
        },
    )
    return enrollment


def revoke_enrollment(
    db: Session, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, enrollment_id: uuid.UUID
) -> BiometricEnrollment:
    enrollment = (
        db.query(BiometricEnrollment)
        .filter(BiometricEnrollment.id == enrollment_id, BiometricEnrollment.tenant_id == tenant_id)
        .first()
    )
    if enrollment is None:
        raise IdentityError("Enrollment not found", status_code=404)
    enrollment.status = EnrollmentStatus.REVOKED
    enrollment.revoked_at = datetime.now(timezone.utc)
    db.flush()
    audit.record(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="biometric_enrollment.revoked",
        resource_type="biometric_enrollment",
        resource_id=str(enrollment.id),
    )
    return enrollment


def get_active_enrollment(db: Session, *, tenant_id: uuid.UUID, member_id: uuid.UUID) -> BiometricEnrollment | None:
    return (
        db.query(BiometricEnrollment)
        .filter(
            BiometricEnrollment.tenant_id == tenant_id,
            BiometricEnrollment.member_id == member_id,
            BiometricEnrollment.status == EnrollmentStatus.ACTIVE,
        )
        .first()
    )
