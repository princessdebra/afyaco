"""Challenge-response liveness: the member is told a randomly-chosen action
("turn your head left") only at the moment they start, performs it on
camera, and the server measures whether the submitted frames' head pose
actually moved the right way — a static photo or a pre-recorded loop cannot
react to an instruction it didn't know in advance.

This is layered ON TOP of the existing passive per-frame liveness check
(app.biometrics.*.perform_liveness_check), not a replacement for it — both
must pass. See services/identity_enrollment.py and services/encounters.py
for how the two are combined.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.biometrics.base import BiometricVerificationProvider
from app.core.config import settings
from app.models.identity import (
    ChallengeAction,
    ChallengeResponseOutcome,
    LivenessChallenge,
    LivenessChallengePurpose,
    LivenessChallengeStatus,
)
from app.services.identity_errors import IdentityError

ACTION_INSTRUCTIONS = {
    ChallengeAction.TURN_LEFT: "Turn your head to the left",
    ChallengeAction.TURN_RIGHT: "Turn your head to the right",
    ChallengeAction.NOD: "Nod your head down, then back up",
}


def issue_challenge(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    purpose: LivenessChallengePurpose,
    member_id: uuid.UUID | None = None,
    encounter_id: uuid.UUID | None = None,
) -> LivenessChallenge:
    action = random.choice(list(ChallengeAction))
    challenge = LivenessChallenge(
        tenant_id=tenant_id,
        member_id=member_id,
        encounter_id=encounter_id,
        purpose=purpose,
        action=action,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.xia_liveness_challenge_ttl_seconds),
    )
    db.add(challenge)
    db.flush()
    return challenge


def _consume(db: Session, *, tenant_id: uuid.UUID, challenge_id: uuid.UUID, purpose: LivenessChallengePurpose) -> LivenessChallenge:
    challenge = (
        db.query(LivenessChallenge)
        .filter(LivenessChallenge.id == challenge_id, LivenessChallenge.tenant_id == tenant_id)
        .with_for_update()
        .first()
    )
    if challenge is None:
        raise IdentityError("Invalid liveness challenge", status_code=404)
    if challenge.purpose != purpose:
        raise IdentityError("Liveness challenge was not issued for this purpose", status_code=403)
    if challenge.status != LivenessChallengeStatus.PENDING:
        raise IdentityError(f"Liveness challenge already {challenge.status.value}", status_code=409)
    if challenge.expires_at < datetime.now(timezone.utc):
        challenge.status = LivenessChallengeStatus.EXPIRED
        db.flush()
        raise IdentityError("Liveness challenge has expired — ask for a new one", status_code=410)

    challenge.status = LivenessChallengeStatus.CONSUMED
    challenge.consumed_at = datetime.now(timezone.utc)
    db.flush()
    return challenge


UNAVAILABLE_DETAIL = (
    "We couldn't get a clear enough view of your face during that. Make sure you're "
    "well-lit, centred in frame, and try again."
)


def _direction_detail(action: ChallengeAction, passed: bool, wrong_direction: bool) -> str:
    """Distinguishes "didn't move enough" from "moved the wrong way" so the
    member gets an actionable message, not just a generic failure (the user-
    visible point of this whole feature — see Enroll.jsx / VerifyVisit.jsx).
    """
    if passed:
        return "Head movement confirmed."
    if action == ChallengeAction.TURN_LEFT:
        if wrong_direction:
            return "You turned right — we asked you to turn LEFT. Please try again."
        return "We didn't detect enough movement. Please turn your head clearly to the LEFT."
    if action == ChallengeAction.TURN_RIGHT:
        if wrong_direction:
            return "You turned left — we asked you to turn RIGHT. Please try again."
        return "We didn't detect enough movement. Please turn your head clearly to the RIGHT."
    return "We didn't detect a clear nod. Please nod your head down and back up more firmly."


async def verify_response(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    provider: BiometricVerificationProvider,
    challenge_id: uuid.UUID,
    purpose: LivenessChallengePurpose,
    frames: list[bytes],
) -> tuple[LivenessChallenge, ChallengeResponseOutcome, bytes, str]:
    """Returns (challenge, outcome, baseline_frame_bytes, detail) — the
    baseline frame (the first frame, captured facing the camera before the
    action starts) is what the rest of the pipeline uses for the actual
    quality/liveness/match checks, since a mid-turn frame is a poor basis for
    face matching. `detail` is a human-readable, actionable explanation —
    distinguishing "wrong direction" from "not enough movement" — so a failed
    attempt tells the member specifically what to fix on retry.
    """
    challenge = _consume(db, tenant_id=tenant_id, challenge_id=challenge_id, purpose=purpose)

    if len(frames) < settings.xia_challenge_min_frames:
        return challenge, ChallengeResponseOutcome.UNAVAILABLE, (frames[0] if frames else b""), UNAVAILABLE_DETAIL

    poses = []
    for frame in frames:
        pose = await provider.estimate_head_pose(frame)
        poses.append(pose)

    baseline_frame = frames[0]
    baseline_pose = poses[0]
    if baseline_pose is None or all(p is None for p in poses[1:]):
        return challenge, ChallengeResponseOutcome.UNAVAILABLE, baseline_frame, UNAVAILABLE_DETAIL

    later_poses = [p for p in poses[1:] if p is not None]
    yaw_threshold = settings.xia_challenge_yaw_threshold_deg

    if challenge.action in (ChallengeAction.TURN_LEFT, ChallengeAction.TURN_RIGHT):
        yaw_deltas = [p.yaw - baseline_pose.yaw for p in later_poses]
        max_delta, min_delta = max(yaw_deltas), min(yaw_deltas)
        if challenge.action == ChallengeAction.TURN_LEFT:
            passed = min_delta <= -yaw_threshold
            wrong_direction = (not passed) and max_delta >= yaw_threshold
        else:
            passed = max_delta >= yaw_threshold
            wrong_direction = (not passed) and min_delta <= -yaw_threshold
    else:  # NOD
        passed = max(abs(p.pitch - baseline_pose.pitch) for p in later_poses) >= settings.xia_challenge_pitch_threshold_deg
        wrong_direction = False

    detail = _direction_detail(challenge.action, passed, wrong_direction)
    return challenge, (ChallengeResponseOutcome.PASSED if passed else ChallengeResponseOutcome.FAILED), baseline_frame, detail
