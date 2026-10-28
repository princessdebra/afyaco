import base64
import binascii
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.base import TenantAdapter
from app.biometrics.base import BiometricVerificationProvider
from app.core.db import get_db
from app.core.deps import CurrentUser, get_biometric_provider, get_current_user, get_tenant_adapter
from app.models.identity import HospitalEncounter, LivenessChallengePurpose
from app.models.member import Member
from app.models.provider import Provider
from app.models.user import UserRole
from app.schemas.identity import (
    AttemptOut,
    ChallengeOut,
    CompleteVerificationRequest,
    EncounterCreate,
    EncounterOut,
    EnrollmentCreate,
    EnrollmentOut,
    LivenessChallengeOut,
    RetryVerificationRequest,
    StartVerificationOut,
    StartVerificationRequest,
    VerifyResult,
)
from app.services import identity_enrollment as enrollment_service
from app.services import liveness_challenge as liveness_challenge_service
from app.services.encounters import (
    complete_verification,
    create_encounter,
    get_latest_attempt,
    issue_challenge,
    retry_verification,
    start_verification,
)
from app.services.identity_errors import IdentityError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/identity", tags=["identity-assurance"])

FACILITY_ROLES = (UserRole.PROVIDER_PARTICIPANT, UserRole.MINET_OPS, UserRole.TENANT_ADMIN)


def _decode_frames(frames_base64: list[str]) -> list[bytes]:
    out = []
    for i, b64 in enumerate(frames_base64):
        try:
            out.append(base64.b64decode(b64, validate=True))
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(422, f"frames_base64[{i}] is not valid base64") from exc
    return out




@router.post("/enrollments/challenge", response_model=LivenessChallengeOut, status_code=201)
def create_enrollment_challenge(
    member_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    challenge = liveness_challenge_service.issue_challenge(
        db, tenant_id=current.tenant_id, purpose=LivenessChallengePurpose.ENROLLMENT, member_id=member_id
    )
    db.commit()
    return LivenessChallengeOut(
        liveness_challenge_id=challenge.id,
        action=challenge.action,
        instruction=liveness_challenge_service.ACTION_INSTRUCTIONS[challenge.action],
        expires_at=challenge.expires_at,
    )


@router.post("/enrollments", response_model=EnrollmentOut, status_code=201)
async def create_enrollment(
    payload: EnrollmentCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider: BiometricVerificationProvider = Depends(get_biometric_provider),
):
    """Brief §4.4 enrolment. Caller must already be authenticated — this
    endpoint intentionally does not itself perform the "insurer-approved
    identity-proofing step" the brief requires before biometric enrolment
    (brief §4.1); that step is a remaining dependency, documented in the
    feature README, not something this endpoint fabricates.
    """
    frames = _decode_frames(payload.frames_base64)
    try:
        enrollment = await enrollment_service.enroll_member(
            db,
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            provider=provider,
            member_id=payload.member_id,
            liveness_challenge_id=payload.liveness_challenge_id,
            frames=frames,
            consent_ref=payload.consent_ref,
        )
        db.commit()
    except IdentityError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.message) from exc
    db.refresh(enrollment)
    return enrollment


@router.get("/enrollments/{member_id}", response_model=EnrollmentOut | None)
def get_enrollment(
    member_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return enrollment_service.get_active_enrollment(db, tenant_id=current.tenant_id, member_id=member_id)


@router.post("/enrollments/{enrollment_id}/revoke", response_model=EnrollmentOut)
def revoke_enrollment(
    enrollment_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        enrollment = enrollment_service.revoke_enrollment(
            db, tenant_id=current.tenant_id, actor_user_id=current.user_id, enrollment_id=enrollment_id
        )
        db.commit()
    except IdentityError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.message) from exc
    db.refresh(enrollment)
    return enrollment


@router.post("/encounters", response_model=EncounterOut, status_code=201)
def start_encounter(
    payload: EncounterCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current.role not in FACILITY_ROLES:
        raise HTTPException(403, "Only facility/operations staff can initiate an encounter")
    try:
        encounter = create_encounter(
            db,
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            member_id=payload.member_id,
            facility_provider_id=payload.facility_provider_id,
            appointment_id=payload.appointment_id,
        )
        db.commit()
    except IdentityError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.message) from exc
    db.refresh(encounter)
    return encounter


@router.get("/encounters/{encounter_id}", response_model=EncounterOut)
def get_encounter(
    encounter_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    encounter = (
        db.query(HospitalEncounter)
        .filter(HospitalEncounter.id == encounter_id, HospitalEncounter.tenant_id == current.tenant_id)
        .first()
    )
    if encounter is None:
        raise HTTPException(404, "Encounter not found")
    return encounter


@router.get("/encounters/{encounter_id}/attempt", response_model=AttemptOut | None)
def get_encounter_attempt(
    encounter_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full diagnostic breakdown — facility/operations staff only. The member-
    facing /verify/complete response is deliberately the only thing a member
    themselves can see; this is the real channel for staff to see the full
    picture (quality, both liveness checks, match score, location distance).
    """
    if current.role not in FACILITY_ROLES:
        raise HTTPException(403, "Only facility/operations staff can view verification detail")
    encounter = (
        db.query(HospitalEncounter)
        .filter(HospitalEncounter.id == encounter_id, HospitalEncounter.tenant_id == current.tenant_id)
        .first()
    )
    if encounter is None:
        raise HTTPException(404, "Encounter not found")
    attempt = get_latest_attempt(db, tenant_id=current.tenant_id, encounter_id=encounter_id)
    if attempt is None:
        return None
    member = db.query(Member).filter(Member.id == encounter.member_id).first()
    facility = db.query(Provider).filter(Provider.id == encounter.facility_provider_id).first()
    return AttemptOut(
        attempt_id=attempt.id,
        encounter_id=attempt.encounter_id,
        member_name=member.full_name if member else "Unknown member",
        facility_name=facility.name if facility else "Unknown facility",
        quality_outcome=attempt.quality_outcome,
        liveness_outcome=attempt.liveness_outcome,
        challenge_response_outcome=attempt.challenge_response_outcome,
        match_outcome=attempt.match_outcome,
        match_score=attempt.match_score,
        location_outcome=attempt.location_outcome,
        location_distance_m=attempt.location_distance_m,
        overall_outcome=attempt.overall_outcome,
        created_at=attempt.created_at,
    )


@router.post("/encounters/{encounter_id}/challenge", response_model=ChallengeOut)
def create_challenge(
    encounter_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current.role not in FACILITY_ROLES:
        raise HTTPException(403, "Only facility/operations staff can issue a verification challenge")
    encounter = (
        db.query(HospitalEncounter)
        .filter(HospitalEncounter.id == encounter_id, HospitalEncounter.tenant_id == current.tenant_id)
        .first()
    )
    if encounter is None:
        raise HTTPException(404, "Encounter not found")
    try:
        challenge, token = issue_challenge(db, tenant_id=current.tenant_id, actor_user_id=current.user_id, encounter=encounter)
        db.commit()
    except IdentityError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.message) from exc
    return ChallengeOut(challenge_id=challenge.id, token=token, expires_at=challenge.expires_at)


@router.post("/verify/start", response_model=StartVerificationOut)
async def verify_start(
    payload: StartVerificationRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consumes the hospital's one-time QR challenge and issues the random
    challenge-response action (brief §6.3 + the challenge-response addition).
    Split from /verify/complete so the UI can show the instruction before the
    camera opens.
    """
    try:
        encounter, live_challenge = await start_verification(
            db,
            tenant_id=current.tenant_id,
            challenge_token=payload.challenge_token,
            facility_provider_id=payload.facility_provider_id,
        )
        db.commit()
    except IdentityError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.message) from exc
    return StartVerificationOut(
        encounter_id=encounter.id,
        liveness_challenge_id=live_challenge.id,
        action=live_challenge.action,
        instruction=liveness_challenge_service.ACTION_INSTRUCTIONS[live_challenge.action],
        expires_at=live_challenge.expires_at,
    )


@router.post("/verify/retry", response_model=StartVerificationOut)
def verify_retry(
    payload: RetryVerificationRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lets a member try again after a failed/ambiguous head-movement check
    without needing a new hospital QR scan — the QR was already consumed by
    /verify/start and is one-time only; only the movement challenge repeats.
    """
    try:
        encounter, live_challenge = retry_verification(db, tenant_id=current.tenant_id, encounter_id=payload.encounter_id)
        db.commit()
    except IdentityError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.message) from exc
    return StartVerificationOut(
        encounter_id=encounter.id,
        liveness_challenge_id=live_challenge.id,
        action=live_challenge.action,
        instruction=liveness_challenge_service.ACTION_INSTRUCTIONS[live_challenge.action],
        expires_at=live_challenge.expires_at,
    )


@router.post("/verify/complete", response_model=VerifyResult)
async def verify_complete(
    payload: CompleteVerificationRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    biometric_provider: BiometricVerificationProvider = Depends(get_biometric_provider),
    tenant_adapter: TenantAdapter = Depends(get_tenant_adapter),
):
    """Brief §5/§7: the member submits the frame burst captured while
    performing the instructed action (+ optional location). All authoritative
    decisions are computed server-side from the challenge, enrolment and
    adapter — nothing in the request body is trusted as a verification result
    in itself (brief §7.3).
    """
    frames = _decode_frames(payload.frames_base64)
    try:
        attempt, response_detail = await complete_verification(
            db,
            tenant_id=current.tenant_id,
            biometric_provider=biometric_provider,
            tenant_adapter=tenant_adapter,
            liveness_challenge_id=payload.liveness_challenge_id,
            frames=frames,
            location=payload.location,
        )
        db.commit()
    except IdentityError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.message) from exc

    encounter = db.query(HospitalEncounter).filter(HospitalEncounter.id == attempt.encounter_id).first()
    member = db.query(Member).filter(Member.id == encounter.member_id).first()
    facility = db.query(Provider).filter(Provider.id == encounter.facility_provider_id).first()
    return VerifyResult(
        attempt_id=attempt.id,
        encounter_id=attempt.encounter_id,
        member_name=member.full_name if member else "Unknown member",
        facility_name=facility.name if facility else "Unknown facility",
        quality_outcome=attempt.quality_outcome,
        liveness_outcome=attempt.liveness_outcome,
        challenge_response_outcome=attempt.challenge_response_outcome,
        challenge_response_detail=response_detail,
        match_outcome=attempt.match_outcome,
        match_score=attempt.match_score,
        location_outcome=attempt.location_outcome,
        location_distance_m=attempt.location_distance_m,
        overall_outcome=attempt.overall_outcome,
        encounter_status=encounter.status,
        eligibility_status=encounter.eligibility_status,
    )
