import hashlib
import math
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.adapters.base import TenantAdapter
from app.biometrics.base import (
    BiometricVerificationProvider,
    LivenessDecision,
    MatchDecision,
    QualityDecision,
)
from app.core.config import settings
from app.models.appointment import Appointment
from app.models.identity import (
    BiometricEnrollment,
    ChallengeResponseOutcome,
    ChallengeStatus,
    EligibilityStatus,
    EncounterStatus,
    HospitalEncounter,
    IdentityStatus,
    IdentityVerificationAttempt,
    LivenessChallenge,
    LivenessChallengePurpose,
    LivenessOutcome,
    LocationOutcome,
    MatchOutcome,
    OverallOutcome,
    QualityOutcome,
    VerificationChallenge,
)
from app.models.member import Member
from app.models.provider import Provider
from app.services import audit, liveness_challenge as liveness_challenge_service
from app.services.identity_enrollment import get_active_enrollment
from app.services.identity_errors import IdentityError

EARTH_RADIUS_M = 6_371_000


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def create_encounter(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    member_id: uuid.UUID,
    facility_provider_id: uuid.UUID,
    appointment_id: uuid.UUID | None,
) -> HospitalEncounter:
    facility = (
        db.query(Provider)
        .filter(Provider.id == facility_provider_id, Provider.tenant_id == tenant_id, Provider.is_active.is_(True))
        .first()
    )
    if facility is None:
        raise IdentityError("Facility not found or not active", status_code=404)

    if appointment_id is not None:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id, Appointment.tenant_id == tenant_id).first()
        if appt is None:
            raise IdentityError("Appointment not found", status_code=404)

    encounter = HospitalEncounter(
        tenant_id=tenant_id,
        member_id=member_id,
        facility_provider_id=facility_provider_id,
        initiated_by_user_id=actor_user_id,
        appointment_id=appointment_id,
        status=EncounterStatus.CREATED,
    )
    db.add(encounter)
    db.flush()
    audit.record(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="encounter.created",
        resource_type="hospital_encounter",
        resource_id=str(encounter.id),
    )
    return encounter


def issue_challenge(
    db: Session, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, encounter: HospitalEncounter
) -> tuple[VerificationChallenge, str]:
    """Brief §6.3: cryptographically random, single-use, short-lived, bound to
    this encounter + facility. Only the hash is persisted — the plaintext
    token is returned once and never stored.
    """
    if encounter.status not in (EncounterStatus.CREATED, EncounterStatus.CHALLENGE_ISSUED):
        raise IdentityError(f"Cannot issue a challenge for an encounter in status '{encounter.status.value}'", status_code=409)

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    challenge = VerificationChallenge(
        tenant_id=tenant_id,
        encounter_id=encounter.id,
        facility_provider_id=encounter.facility_provider_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.xia_challenge_ttl_seconds),
    )
    db.add(challenge)
    encounter.status = EncounterStatus.CHALLENGE_ISSUED
    db.flush()
    audit.record(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="encounter.challenge_issued",
        resource_type="verification_challenge",
        resource_id=str(challenge.id),
        context={"encounter_id": str(encounter.id)},
    )
    return challenge, token


def _consume_challenge(db: Session, *, tenant_id: uuid.UUID, token: str, facility_provider_id: uuid.UUID) -> VerificationChallenge:
    """Atomic single-use consumption (brief §6.3). `with_for_update()` takes a
    row lock inside the current transaction so two concurrent requests cannot
    both successfully consume the same challenge — the second blocks until
    the first commits, then sees status != PENDING and is rejected.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    challenge = (
        db.query(VerificationChallenge)
        .filter(VerificationChallenge.tenant_id == tenant_id, VerificationChallenge.token_hash == token_hash)
        .with_for_update()
        .first()
    )
    if challenge is None:
        raise IdentityError("Invalid challenge", status_code=404)
    if challenge.facility_provider_id != facility_provider_id:
        raise IdentityError("Challenge is not valid for this facility", status_code=403)
    if challenge.status != ChallengeStatus.PENDING:
        raise IdentityError(f"Challenge already {challenge.status.value}", status_code=409)
    if challenge.expires_at < datetime.now(timezone.utc):
        challenge.status = ChallengeStatus.EXPIRED
        db.flush()
        raise IdentityError("Challenge has expired", status_code=410)

    challenge.status = ChallengeStatus.CONSUMED
    challenge.consumed_at = datetime.now(timezone.utc)
    db.flush()
    return challenge


def _evaluate_location(
    facility: Provider, location
) -> tuple[LocationOutcome, float | None]:
    if location is None:
        return LocationOutcome.UNAVAILABLE, None
    if facility.latitude is None or facility.longitude is None:
        return LocationOutcome.UNAVAILABLE, None

    age_s = (datetime.now(timezone.utc) - location.captured_at).total_seconds()
    if age_s > settings.xia_max_location_age_seconds or age_s < -30:
        return LocationOutcome.STALE, None
    if location.accuracy_m <= 0 or location.accuracy_m > settings.xia_max_gps_accuracy_meters:
        return LocationOutcome.IMPLAUSIBLE, None

    distance_m = _haversine_m(location.latitude, location.longitude, facility.latitude, facility.longitude)
    tolerance = (facility.geofence_meters or settings.xia_default_geofence_meters) + location.accuracy_m
    if distance_m <= tolerance:
        return LocationOutcome.ACCEPTED, distance_m
    return LocationOutcome.OUT_OF_RANGE, distance_m


def _decide_overall(quality, liveness, challenge_response, match, location) -> OverallOutcome:
    """xia-policy-v1 (deliberately simple — see services/encounters.py module
    docs for rationale): liveness, challenge-response and quality failures
    are hard fails; a non-match is a hard fail; an unavailable/out-of-range/
    stale location — or a challenge-response that couldn't be measured — is a
    soft fail routed to manual review rather than blocking care (brief §7.4).
    """
    if match == MatchOutcome.NOT_ENROLLED:
        return OverallOutcome.FAILED
    if quality == QualityOutcome.REJECTED:
        return OverallOutcome.FAILED
    if liveness == LivenessOutcome.FAILED:
        # See app/core/config.py xia_passive_liveness_enforcement — this
        # model has been observed to misfire on real phone-selfie captures;
        # "soft" downgrades a failure here to manual review instead of an
        # automatic hard block. Challenge-response liveness below remains a
        # hard gate regardless.
        return OverallOutcome.FAILED if settings.xia_passive_liveness_enforcement == "hard" else OverallOutcome.MANUAL_REVIEW_REQUIRED
    if challenge_response == ChallengeResponseOutcome.FAILED:
        return OverallOutcome.FAILED
    if match == MatchOutcome.NO_MATCH:
        return OverallOutcome.FAILED
    if liveness == LivenessOutcome.UNAVAILABLE or match == MatchOutcome.PROVIDER_UNAVAILABLE:
        return OverallOutcome.MANUAL_REVIEW_REQUIRED
    if challenge_response == ChallengeResponseOutcome.UNAVAILABLE:
        return OverallOutcome.MANUAL_REVIEW_REQUIRED
    if location in (LocationOutcome.OUT_OF_RANGE, LocationOutcome.IMPLAUSIBLE, LocationOutcome.STALE):
        return OverallOutcome.MANUAL_REVIEW_REQUIRED
    return OverallOutcome.PASSED


async def start_verification(
    db: Session, *, tenant_id: uuid.UUID, challenge_token: str, facility_provider_id: uuid.UUID
) -> tuple[HospitalEncounter, LivenessChallenge]:
    """Consumes the hospital's one-time QR challenge (brief §6.3) and, in the
    same step, issues the random challenge-response action the member must
    perform — splitting "scan the QR" from "do the head movement" into two
    calls so the UI can show the instruction before the camera opens.
    """
    challenge = _consume_challenge(db, tenant_id=tenant_id, token=challenge_token, facility_provider_id=facility_provider_id)
    encounter = db.query(HospitalEncounter).filter(HospitalEncounter.id == challenge.encounter_id).first()
    if encounter is None or encounter.status == EncounterStatus.CANCELLED:
        raise IdentityError("Encounter not found or cancelled", status_code=404)

    encounter.status = EncounterStatus.VERIFYING
    encounter.identity_status = IdentityStatus.IN_PROGRESS
    live_challenge = liveness_challenge_service.issue_challenge(
        db, tenant_id=tenant_id, purpose=LivenessChallengePurpose.VERIFICATION, encounter_id=encounter.id
    )
    db.flush()
    return encounter, live_challenge


def retry_verification(db: Session, *, tenant_id: uuid.UUID, encounter_id: uuid.UUID) -> tuple[HospitalEncounter, LivenessChallenge]:
    """Issues a fresh challenge-response action for an encounter that already
    exists (the hospital's one-time QR was already consumed in
    start_verification and is never needed again) — lets a member retry after
    a wrong-direction or no-movement attempt without asking the front desk
    for a new QR code.
    """
    encounter = (
        db.query(HospitalEncounter)
        .filter(HospitalEncounter.id == encounter_id, HospitalEncounter.tenant_id == tenant_id)
        .first()
    )
    if encounter is None:
        raise IdentityError("Encounter not found", status_code=404)
    if encounter.status in (EncounterStatus.VERIFIED, EncounterStatus.CANCELLED):
        raise IdentityError(f"Cannot retry an encounter in status '{encounter.status.value}'", status_code=409)

    encounter.status = EncounterStatus.VERIFYING
    encounter.identity_status = IdentityStatus.IN_PROGRESS
    live_challenge = liveness_challenge_service.issue_challenge(
        db, tenant_id=tenant_id, purpose=LivenessChallengePurpose.VERIFICATION, encounter_id=encounter.id
    )
    db.flush()
    return encounter, live_challenge


async def complete_verification(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    biometric_provider: BiometricVerificationProvider,
    tenant_adapter: TenantAdapter,
    liveness_challenge_id: uuid.UUID,
    frames: list[bytes],
    location=None,
) -> tuple[IdentityVerificationAttempt, str]:
    live_challenge, response_outcome, baseline_frame, response_detail = await liveness_challenge_service.verify_response(
        db,
        tenant_id=tenant_id,
        provider=biometric_provider,
        challenge_id=liveness_challenge_id,
        purpose=LivenessChallengePurpose.VERIFICATION,
        frames=frames,
    )
    encounter = db.query(HospitalEncounter).filter(HospitalEncounter.id == live_challenge.encounter_id).first()
    if encounter is None:
        raise IdentityError("Encounter not found", status_code=404)

    facility = db.query(Provider).filter(Provider.id == encounter.facility_provider_id).first()
    member = db.query(Member).filter(Member.id == encounter.member_id).first()

    enrollment = get_active_enrollment(db, tenant_id=tenant_id, member_id=encounter.member_id)

    if enrollment is None:
        quality_outcome = QualityOutcome.REJECTED
        liveness_outcome = LivenessOutcome.UNAVAILABLE
        match_outcome = MatchOutcome.NOT_ENROLLED
        match_score = None
    else:
        quality = await biometric_provider.assess_capture_quality(baseline_frame)
        quality_outcome = QualityOutcome(quality.decision.value)

        liveness = await biometric_provider.perform_liveness_check(baseline_frame)
        liveness_outcome = LivenessOutcome(liveness.decision.value)

        match_result = await biometric_provider.compare_with_enrollment(enrollment.template_ref, baseline_frame)
        match_outcome = (
            MatchOutcome.MATCH if match_result.decision == MatchDecision.MATCH
            else MatchOutcome.PROVIDER_UNAVAILABLE if match_result.decision == MatchDecision.PROVIDER_UNAVAILABLE
            else MatchOutcome.NO_MATCH
        )
        match_score = match_result.score

    location_outcome, distance_m = _evaluate_location(facility, location)
    overall = _decide_overall(quality_outcome, liveness_outcome, response_outcome, match_outcome, location_outcome)

    attempt = IdentityVerificationAttempt(
        tenant_id=tenant_id,
        member_id=encounter.member_id,
        encounter_id=encounter.id,
        enrollment_id=enrollment.id if enrollment else None,
        liveness_challenge_id=live_challenge.id,
        quality_outcome=quality_outcome,
        liveness_outcome=liveness_outcome,
        challenge_response_outcome=response_outcome,
        match_outcome=match_outcome,
        match_score=match_score,
        location_outcome=location_outcome,
        location_distance_m=distance_m,
        overall_outcome=overall,
        provider_key=biometric_provider.key,
    )
    db.add(attempt)

    if overall == OverallOutcome.PASSED:
        encounter.identity_status = IdentityStatus.PASSED
        encounter.status = EncounterStatus.VERIFIED
    elif overall == OverallOutcome.MANUAL_REVIEW_REQUIRED:
        encounter.identity_status = IdentityStatus.MANUAL_REVIEW_REQUIRED
        # encounter.status stays VERIFYING pending manual review
    else:
        encounter.identity_status = IdentityStatus.FAILED
        encounter.status = EncounterStatus.FAILED

    db.flush()

    audit.record(
        db,
        tenant_id=tenant_id,
        actor_user_id=None,
        action="identity_verification.attempted",
        resource_type="identity_verification_attempt",
        resource_id=str(attempt.id),
        context={
            "encounter_id": str(encounter.id),
            "quality": quality_outcome.value,
            "liveness": liveness_outcome.value,
            "challenge_response": response_outcome.value,
            "match": match_outcome.value,
            "location": location_outcome.value,
            "overall": overall.value,
        },
    )

    # Eligibility is checked only once identity has actually passed (brief §6
    # step 10) — never inferred from identity verification, and never
    # defaulted to "eligible" if the adapter fails (brief §8).
    if overall == OverallOutcome.PASSED and member is not None:
        try:
            result = await tenant_adapter.check_eligibility(
                member_external_ref=member.external_ref,
                service_code="hospital_encounter",
                provider_external_ref=facility.external_ref,
                on_date=datetime.now(timezone.utc).date().isoformat(),
            )
            encounter.eligibility_status = (
                EligibilityStatus.CONFIRMED if result.outcome == "eligible"
                else EligibilityStatus.NOT_ELIGIBLE if result.outcome == "not_eligible"
                else EligibilityStatus.PENDING
            )
        except Exception:
            encounter.eligibility_status = EligibilityStatus.UNAVAILABLE
        db.flush()
        audit.record(
            db,
            tenant_id=tenant_id,
            actor_user_id=None,
            action="encounter.eligibility_checked",
            resource_type="hospital_encounter",
            resource_id=str(encounter.id),
            context={"eligibility_status": encounter.eligibility_status.value},
        )

    return attempt, response_detail


def get_latest_attempt(db: Session, *, tenant_id: uuid.UUID, encounter_id: uuid.UUID) -> IdentityVerificationAttempt | None:
    return (
        db.query(IdentityVerificationAttempt)
        .filter(IdentityVerificationAttempt.tenant_id == tenant_id, IdentityVerificationAttempt.encounter_id == encounter_id)
        .order_by(IdentityVerificationAttempt.created_at.desc())
        .first()
    )
