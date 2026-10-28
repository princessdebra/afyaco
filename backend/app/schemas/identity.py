import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.identity import (
    ChallengeAction,
    ChallengeResponseOutcome,
    EligibilityStatus,
    EncounterStatus,
    EnrollmentStatus,
    IdentityStatus,
    LivenessOutcome,
    LocationOutcome,
    MatchOutcome,
    OverallOutcome,
    QualityOutcome,
)


class LivenessChallengeOut(BaseModel):
    liveness_challenge_id: uuid.UUID
    action: ChallengeAction
    instruction: str
    expires_at: datetime


class EnrollmentCreate(BaseModel):
    member_id: uuid.UUID
    liveness_challenge_id: uuid.UUID = Field(description="From POST /identity/enrollments/challenge")
    frames_base64: list[str] = Field(
        min_length=1, description="Burst captured during the challenge action; frame[0] must be the frontal baseline shot"
    )
    consent_ref: str = Field(description="Pointer to the recorded consent/legal-basis acknowledgement")


class EnrollmentOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    status: EnrollmentStatus
    provider_key: str
    template_version: str
    created_at: datetime
    revoked_at: datetime | None

    class Config:
        from_attributes = True


class EncounterCreate(BaseModel):
    member_id: uuid.UUID
    facility_provider_id: uuid.UUID
    appointment_id: uuid.UUID | None = None


class EncounterOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    facility_provider_id: uuid.UUID
    status: EncounterStatus
    identity_status: IdentityStatus
    eligibility_status: EligibilityStatus
    created_at: datetime

    class Config:
        from_attributes = True


class ChallengeOut(BaseModel):
    challenge_id: uuid.UUID
    token: str = Field(description="Plaintext, single-use. Returned only once — not retrievable later.")
    expires_at: datetime


class LocationSignal(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: float
    captured_at: datetime


class StartVerificationRequest(BaseModel):
    challenge_token: str
    facility_provider_id: uuid.UUID


class StartVerificationOut(BaseModel):
    encounter_id: uuid.UUID
    liveness_challenge_id: uuid.UUID
    action: ChallengeAction
    instruction: str
    expires_at: datetime


class RetryVerificationRequest(BaseModel):
    encounter_id: uuid.UUID


class CompleteVerificationRequest(BaseModel):
    liveness_challenge_id: uuid.UUID
    frames_base64: list[str] = Field(min_length=1, description="frame[0] must be the frontal baseline shot")
    location: LocationSignal | None = None


class AttemptOut(BaseModel):
    """Full diagnostic breakdown of the latest verification attempt on an
    encounter — provider/operations-facing only (see app/api/v1/identity.py
    get_latest_attempt). Members see a deliberately reduced view; this is
    the real channel staff use to see the full picture.
    """

    attempt_id: uuid.UUID
    encounter_id: uuid.UUID
    member_name: str
    facility_name: str
    quality_outcome: QualityOutcome
    liveness_outcome: LivenessOutcome
    challenge_response_outcome: ChallengeResponseOutcome
    match_outcome: MatchOutcome
    match_score: float | None
    location_outcome: LocationOutcome
    location_distance_m: float | None
    overall_outcome: OverallOutcome
    created_at: datetime


class VerifyResult(BaseModel):
    attempt_id: uuid.UUID
    encounter_id: uuid.UUID
    member_name: str
    facility_name: str
    quality_outcome: QualityOutcome
    liveness_outcome: LivenessOutcome
    challenge_response_outcome: ChallengeResponseOutcome
    challenge_response_detail: str
    match_outcome: MatchOutcome
    match_score: float | None
    location_outcome: LocationOutcome
    location_distance_m: float | None
    overall_outcome: OverallOutcome
    encounter_status: EncounterStatus
    eligibility_status: EligibilityStatus
