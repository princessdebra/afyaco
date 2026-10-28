import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.adapters.stub import StubAdapter
from app.biometrics.mock import MockBiometricProvider
from app.models.identity import (
    ChallengeAction,
    ChallengeResponseOutcome,
    EligibilityStatus,
    EncounterStatus,
    IdentityStatus,
    LivenessChallenge,
    LivenessChallengePurpose,
    LocationOutcome,
    OverallOutcome,
)
from app.schemas.identity import LocationSignal
from app.services import identity_enrollment as enrollment_service
from app.services import liveness_challenge as liveness_challenge_service
from app.services.encounters import complete_verification, create_encounter, issue_challenge, start_verification
from app.services.identity_errors import IdentityError

pytestmark = pytest.mark.asyncio

GOOD_IMAGE = b"JPEGDATA" * 200  # > MIN_BYTES_FOR_ACCEPTABLE_QUALITY
OTHER_IMAGE = b"DIFFERENTJPEG" * 200
TOO_SMALL_IMAGE = b"tiny"
SPOOF_IMAGE = b"SPOOF" + GOOD_IMAGE

provider = MockBiometricProvider()
adapter = StubAdapter()

# Mock pose frames for each action, deliberately exceeding the configured
# thresholds (yaw 15deg, pitch 12deg) so a "correct response" is unambiguous.
_GOOD_RESPONSE = {
    ChallengeAction.TURN_LEFT: [b"POSE:-25:0:pad", b"POSE:-28:0:pad"],
    ChallengeAction.TURN_RIGHT: [b"POSE:25:0:pad", b"POSE:28:0:pad"],
    ChallengeAction.NOD: [b"POSE:0:20:pad", b"POSE:0:18:pad"],
}
_WRONG_RESPONSE = [b"POSE:1:0:pad", b"POSE:0:1:pad"]  # well under any threshold, any action
_OPPOSITE_RESPONSE = {
    ChallengeAction.TURN_LEFT: [b"POSE:25:0:pad", b"POSE:28:0:pad"],  # turned right instead
    ChallengeAction.TURN_RIGHT: [b"POSE:-25:0:pad", b"POSE:-28:0:pad"],  # turned left instead
}


def _frames(action, baseline=GOOD_IMAGE, respond_correctly=True):
    tail = _GOOD_RESPONSE[action] if respond_correctly else _WRONG_RESPONSE
    return [baseline] + tail


async def _enroll(db, tenant, member, staff_user, baseline=GOOD_IMAGE, respond_correctly=True, consent="consent-1"):
    challenge = liveness_challenge_service.issue_challenge(
        db, tenant_id=tenant.id, purpose=LivenessChallengePurpose.ENROLLMENT, member_id=member.id
    )
    db.commit()
    frames = _frames(challenge.action, baseline, respond_correctly)
    return await enrollment_service.enroll_member(
        db, tenant_id=tenant.id, actor_user_id=staff_user.id, provider=provider,
        member_id=member.id, liveness_challenge_id=challenge.id, frames=frames, consent_ref=consent,
    )


async def _complete(db, tenant, challenge_token, facility, respond_correctly=True, baseline=GOOD_IMAGE, location=None):
    encounter, live_challenge = await start_verification(
        db, tenant_id=tenant.id, challenge_token=challenge_token, facility_provider_id=facility.id
    )
    db.commit()
    frames = _frames(live_challenge.action, baseline, respond_correctly)
    attempt, _detail = await complete_verification(
        db, tenant_id=tenant.id, biometric_provider=provider, tenant_adapter=adapter,
        liveness_challenge_id=live_challenge.id, frames=frames, location=location,
    )
    return encounter, attempt


# --- Enrollment ---------------------------------------------------------

async def test_enroll_member_succeeds(db, tenant, member, staff_user):
    enrollment = await _enroll(db, tenant, member, staff_user)
    assert enrollment.status.value == "active"
    assert enrollment.provider_key == "mock"


async def test_enroll_member_rejects_low_quality_capture(db, tenant, member, staff_user):
    with pytest.raises(IdentityError) as exc:
        await _enroll(db, tenant, member, staff_user, baseline=TOO_SMALL_IMAGE)
    assert exc.value.status_code == 422


async def test_enroll_member_rejects_failed_liveness(db, tenant, member, staff_user):
    with pytest.raises(IdentityError) as exc:
        await _enroll(db, tenant, member, staff_user, baseline=SPOOF_IMAGE)
    assert exc.value.status_code == 422


async def test_enroll_member_rejects_wrong_head_movement(db, tenant, member, staff_user):
    """The member was asked to e.g. turn left but the submitted frames show no
    real head movement — must not enroll even though the baseline photo
    itself is a fine, live photo."""
    with pytest.raises(IdentityError) as exc:
        await _enroll(db, tenant, member, staff_user, respond_correctly=False)
    assert exc.value.status_code == 422


async def test_cannot_enroll_twice_without_revoking(db, tenant, member, staff_user):
    await _enroll(db, tenant, member, staff_user, consent="consent-1")
    with pytest.raises(IdentityError) as exc:
        await _enroll(db, tenant, member, staff_user, consent="consent-2")
    assert exc.value.status_code == 409


async def test_revoke_then_reenroll_succeeds(db, tenant, member, staff_user):
    first = await _enroll(db, tenant, member, staff_user, consent="consent-1")
    enrollment_service.revoke_enrollment(db, tenant_id=tenant.id, actor_user_id=staff_user.id, enrollment_id=first.id)
    second = await _enroll(db, tenant, member, staff_user, consent="consent-3")
    assert second.id != first.id
    assert second.status.value == "active"


# --- Hospital QR challenge (single-use, facility-bound) -------------------

async def test_challenge_is_single_use(db, tenant, member, facility, staff_user):
    encounter = create_encounter(
        db, tenant_id=tenant.id, actor_user_id=staff_user.id, member_id=member.id,
        facility_provider_id=facility.id, appointment_id=None,
    )
    _, token = issue_challenge(db, tenant_id=tenant.id, actor_user_id=staff_user.id, encounter=encounter)
    db.commit()

    await start_verification(db, tenant_id=tenant.id, challenge_token=token, facility_provider_id=facility.id)
    db.commit()

    with pytest.raises(IdentityError) as exc:
        await start_verification(db, tenant_id=tenant.id, challenge_token=token, facility_provider_id=facility.id)
    assert exc.value.status_code == 409


async def test_challenge_rejected_for_wrong_facility(db, tenant, member, facility, other_facility, staff_user):
    encounter = create_encounter(
        db, tenant_id=tenant.id, actor_user_id=staff_user.id, member_id=member.id,
        facility_provider_id=facility.id, appointment_id=None,
    )
    _, token = issue_challenge(db, tenant_id=tenant.id, actor_user_id=staff_user.id, encounter=encounter)
    db.commit()

    with pytest.raises(IdentityError) as exc:
        await start_verification(db, tenant_id=tenant.id, challenge_token=token, facility_provider_id=other_facility.id)
    assert exc.value.status_code == 403


async def test_expired_challenge_rejected(db, tenant, member, facility, staff_user):
    encounter = create_encounter(
        db, tenant_id=tenant.id, actor_user_id=staff_user.id, member_id=member.id,
        facility_provider_id=facility.id, appointment_id=None,
    )
    challenge, token = issue_challenge(db, tenant_id=tenant.id, actor_user_id=staff_user.id, encounter=encounter)
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    with pytest.raises(IdentityError) as exc:
        await start_verification(db, tenant_id=tenant.id, challenge_token=token, facility_provider_id=facility.id)
    assert exc.value.status_code == 410


async def test_unknown_token_rejected(db, tenant, facility):
    with pytest.raises(IdentityError) as exc:
        await start_verification(db, tenant_id=tenant.id, challenge_token="not-a-real-token", facility_provider_id=facility.id)
    assert exc.value.status_code == 404


# --- Verification policy --------------------------------------------------

async def _setup_enrolled_encounter(db, tenant, member, facility, staff_user, baseline=GOOD_IMAGE):
    await _enroll(db, tenant, member, staff_user, baseline=baseline)
    encounter = create_encounter(
        db, tenant_id=tenant.id, actor_user_id=staff_user.id, member_id=member.id,
        facility_provider_id=facility.id, appointment_id=None,
    )
    _, token = issue_challenge(db, tenant_id=tenant.id, actor_user_id=staff_user.id, encounter=encounter)
    db.commit()
    return encounter, token


async def test_correct_member_passes(db, tenant, member, facility, staff_user):
    encounter, token = await _setup_enrolled_encounter(db, tenant, member, facility, staff_user)
    encounter, attempt = await _complete(db, tenant, token, facility)
    db.commit()
    assert attempt.overall_outcome == OverallOutcome.PASSED
    assert attempt.challenge_response_outcome == ChallengeResponseOutcome.PASSED
    db.refresh(encounter)
    assert encounter.status == EncounterStatus.VERIFIED
    assert encounter.identity_status == IdentityStatus.PASSED
    # stub adapter has no record of this synthetic test member -> not_eligible, never silently "confirmed"
    assert encounter.eligibility_status == EligibilityStatus.NOT_ELIGIBLE


async def test_different_person_fails(db, tenant, member, facility, staff_user):
    encounter, token = await _setup_enrolled_encounter(db, tenant, member, facility, staff_user)
    encounter, attempt = await _complete(db, tenant, token, facility, baseline=OTHER_IMAGE)
    db.commit()
    assert attempt.overall_outcome == OverallOutcome.FAILED
    assert attempt.match_outcome.value == "no_match"
    db.refresh(encounter)
    assert encounter.status == EncounterStatus.FAILED
    # a failed identity check must never trigger an eligibility lookup
    assert encounter.eligibility_status == EligibilityStatus.NOT_CHECKED


async def test_liveness_failure_cannot_be_overridden_by_match(db, tenant, member, facility, staff_user):
    encounter, token = await _setup_enrolled_encounter(db, tenant, member, facility, staff_user)
    # same bytes as enrollment (would match) but with the mock spoof marker
    spoofed_same_image = b"SPOOF" + GOOD_IMAGE
    encounter, attempt = await _complete(db, tenant, token, facility, baseline=spoofed_same_image)
    db.commit()
    assert attempt.liveness_outcome.value == "failed"
    assert attempt.overall_outcome == OverallOutcome.FAILED


async def test_correct_face_but_wrong_head_movement_fails(db, tenant, member, facility, staff_user):
    """The core anti-replay case: a static photo (or someone who simply holds
    still) presents the enrolled member's own face correctly, and passive
    liveness even passes — but didn't perform the randomly-instructed
    movement, so the response is rejected anyway."""
    encounter, token = await _setup_enrolled_encounter(db, tenant, member, facility, staff_user)
    encounter, attempt = await _complete(db, tenant, token, facility, respond_correctly=False)
    db.commit()
    assert attempt.match_outcome.value == "match"
    assert attempt.liveness_outcome.value == "passed"
    assert attempt.challenge_response_outcome == ChallengeResponseOutcome.FAILED
    assert attempt.overall_outcome == OverallOutcome.FAILED
    db.refresh(encounter)
    assert encounter.status == EncounterStatus.FAILED


async def test_wrong_direction_gives_specific_actionable_message(db, tenant, member, facility, staff_user):
    """Turning the WRONG way (not just failing to move) must say so
    specifically, so the member knows to flip direction on retry rather than
    just "try harder"."""
    await _enroll(db, tenant, member, staff_user)
    encounter = create_encounter(
        db, tenant_id=tenant.id, actor_user_id=staff_user.id, member_id=member.id,
        facility_provider_id=facility.id, appointment_id=None,
    )
    _, token = issue_challenge(db, tenant_id=tenant.id, actor_user_id=staff_user.id, encounter=encounter)
    db.commit()

    # Force a deterministic TURN_LEFT challenge rather than relying on the
    # random pick, so the "opposite direction" response is unambiguous.
    forced = LivenessChallenge(
        tenant_id=tenant.id, encounter_id=encounter.id, purpose=LivenessChallengePurpose.VERIFICATION,
        action=ChallengeAction.TURN_LEFT, expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
    )
    db.add(forced)
    db.commit()

    frames = [GOOD_IMAGE] + _OPPOSITE_RESPONSE[ChallengeAction.TURN_LEFT]
    attempt, detail = await complete_verification(
        db, tenant_id=tenant.id, biometric_provider=provider, tenant_adapter=adapter,
        liveness_challenge_id=forced.id, frames=frames, location=None,
    )
    assert attempt.challenge_response_outcome == ChallengeResponseOutcome.FAILED
    assert "turned right" in detail.lower()
    assert "left" in detail.lower()


async def test_too_few_frames_is_unavailable_not_a_hard_fail(db, tenant, member, facility, staff_user):
    """A technical capture problem (burst too short) is not the same as a
    detected spoof — it should route to manual review, not an automatic
    fraud-equivalent rejection."""
    encounter, token = await _setup_enrolled_encounter(db, tenant, member, facility, staff_user)
    encounter_obj, live_challenge = await start_verification(
        db, tenant_id=tenant.id, challenge_token=token, facility_provider_id=facility.id
    )
    db.commit()
    attempt, _detail = await complete_verification(
        db, tenant_id=tenant.id, biometric_provider=provider, tenant_adapter=adapter,
        liveness_challenge_id=live_challenge.id, frames=[GOOD_IMAGE], location=None,  # only 1 frame, below the minimum
    )
    db.commit()
    assert attempt.challenge_response_outcome == ChallengeResponseOutcome.UNAVAILABLE
    assert attempt.overall_outcome == OverallOutcome.MANUAL_REVIEW_REQUIRED


async def test_not_enrolled_member_fails(db, tenant, member, facility, staff_user):
    encounter = create_encounter(
        db, tenant_id=tenant.id, actor_user_id=staff_user.id, member_id=member.id,
        facility_provider_id=facility.id, appointment_id=None,
    )
    _, token = issue_challenge(db, tenant_id=tenant.id, actor_user_id=staff_user.id, encounter=encounter)
    db.commit()

    encounter, attempt = await _complete(db, tenant, token, facility)
    assert attempt.match_outcome.value == "not_enrolled"
    assert attempt.overall_outcome == OverallOutcome.FAILED


async def test_location_within_geofence_accepted(db, tenant, member, facility, staff_user):
    encounter, token = await _setup_enrolled_encounter(db, tenant, member, facility, staff_user)
    location = LocationSignal(
        latitude=facility.latitude, longitude=facility.longitude, accuracy_m=20, captured_at=datetime.now(timezone.utc)
    )
    encounter, attempt = await _complete(db, tenant, token, facility, location=location)
    assert attempt.location_outcome == LocationOutcome.ACCEPTED
    assert attempt.overall_outcome == OverallOutcome.PASSED


async def test_location_far_from_facility_routes_to_manual_review(db, tenant, member, facility, staff_user):
    encounter, token = await _setup_enrolled_encounter(db, tenant, member, facility, staff_user)
    # ~500km away — nowhere near the facility's geofence
    location = LocationSignal(latitude=-4.05, longitude=39.67, accuracy_m=20, captured_at=datetime.now(timezone.utc))
    encounter, attempt = await _complete(db, tenant, token, facility, location=location)
    assert attempt.location_outcome == LocationOutcome.OUT_OF_RANGE
    assert attempt.overall_outcome == OverallOutcome.MANUAL_REVIEW_REQUIRED
    db.refresh(encounter)
    # a soft (location) signal must not hard-fail or silently pass the encounter
    assert encounter.identity_status == IdentityStatus.MANUAL_REVIEW_REQUIRED


async def test_missing_location_does_not_block_verification(db, tenant, member, facility, staff_user):
    """Brief §7.4: the app must not indefinitely block access to care because
    a phone lacks GPS."""
    encounter, token = await _setup_enrolled_encounter(db, tenant, member, facility, staff_user)
    encounter, attempt = await _complete(db, tenant, token, facility, location=None)
    assert attempt.location_outcome == LocationOutcome.UNAVAILABLE
    assert attempt.overall_outcome == OverallOutcome.PASSED


# --- Cross-tenant isolation -----------------------------------------------

async def test_cross_tenant_facility_not_found(db, tenant, member, staff_user):
    from app.models.provider import Provider, ProviderType
    from app.models.tenant import Tenant, TenantKind

    another_tenant = Tenant(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant", kind=TenantKind.MIP, adapter_key="stub")
    db.add(another_tenant)
    db.commit()

    other_tenant_facility = Provider(
        tenant_id=another_tenant.id,  # a different tenant entirely
        external_ref="FAC-OTHER-TENANT",
        name="Other Tenant Hospital",
        type=ProviderType.FACILITY,
        specialties=["Hospital"],
    )
    db.add(other_tenant_facility)
    db.commit()

    with pytest.raises(IdentityError) as exc:
        create_encounter(
            db, tenant_id=tenant.id, actor_user_id=staff_user.id, member_id=member.id,
            facility_provider_id=other_tenant_facility.id, appointment_id=None,
        )
    assert exc.value.status_code == 404
