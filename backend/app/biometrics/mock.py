"""MOCK BIOMETRIC PROVIDER — development and automated tests ONLY.

This is NOT a biometric security implementation. It does not perform real
face detection, face recognition, or presentation-attack/liveness detection.
It exists so the rest of Xenova Identity Assurance (enrollment, challenge
binding, encounter workflow, API contracts, audit trail) can be built and
exercised end to end without a real vendor contract, and so automated tests
never need real member biometric data.

What it actually does, and why that is NOT acceptable in production:

- "Enrollment reference" = SHA-256 digest of the raw image bytes. A real
  provider returns a protected, typically irreversible biometric template
  produced by a trained face-recognition model — not a reversible digest of
  the input image.
- "Comparison" = exact byte-for-byte equality of two images' digests. This
  only ever matches if the probe image is bit-identical to the enrollment
  image, which cannot be true of two real photographs of the same person
  taken at different times. It provides no actual face-matching capability.
- "Liveness" = a test-only trigger: the literal bytes b"SPOOF" anywhere in
  the payload fail liveness; everything else passes. This has no relation to
  real presentation-attack detection.

`core.config.Settings.environment == "production"` with
`biometric_provider_key == "mock"` must fail startup — see
app.biometrics.registry.get_provider — rather than silently serving this as
if it were real biometric verification.
"""

import hashlib

import re

from app.biometrics.base import (
    BiometricVerificationProvider,
    EnrollmentReference,
    HeadPose,
    LivenessDecision,
    LivenessResult,
    MatchDecision,
    MatchResult,
    ProviderHealth,
    QualityDecision,
    QualityResult,
)

# Test-only convention: a mock "frame" can embed b"POSE:<yaw>:<pitch>:" at the
# start of its bytes to simulate a measured head pose, e.g. b"POSE:-25:0:" +
# filler. No real pose estimation happens here — see module docstring.
_POSE_MARKER = re.compile(rb"^POSE:(-?\d+(?:\.\d+)?):(-?\d+(?:\.\d+)?):")

MIN_BYTES_FOR_ACCEPTABLE_QUALITY = 1024  # arbitrary floor to reject empty/truncated captures
MOCK_THRESHOLD = 0.9


class MockBiometricProvider(BiometricVerificationProvider):
    key = "mock"

    async def assess_capture_quality(self, image_bytes: bytes) -> QualityResult:
        if len(image_bytes) < MIN_BYTES_FOR_ACCEPTABLE_QUALITY:
            return QualityResult(QualityDecision.REJECTED, reason="capture too small/truncated")
        return QualityResult(QualityDecision.ACCEPTABLE)

    async def perform_liveness_check(self, image_bytes: bytes) -> LivenessResult:
        if not image_bytes:
            return LivenessResult(LivenessDecision.UNAVAILABLE, reason="no capture provided")
        if b"SPOOF" in image_bytes:
            return LivenessResult(LivenessDecision.FAILED, reason="mock spoof marker present")
        return LivenessResult(LivenessDecision.PASSED)

    async def create_enrollment_reference(self, image_bytes: bytes) -> EnrollmentReference:
        digest = hashlib.sha256(image_bytes).hexdigest()
        return EnrollmentReference(template_ref=digest, template_version="mock-v1")

    async def compare_with_enrollment(self, template_ref: str, probe_image_bytes: bytes) -> MatchResult:
        probe_digest = hashlib.sha256(probe_image_bytes).hexdigest()
        is_match = probe_digest == template_ref
        return MatchResult(
            decision=MatchDecision.MATCH if is_match else MatchDecision.NO_MATCH,
            score=1.0 if is_match else 0.0,
            threshold=MOCK_THRESHOLD,
        )

    async def get_provider_health(self) -> ProviderHealth:
        return ProviderHealth(healthy=True, detail="mock provider, no external dependency")

    async def estimate_head_pose(self, image_bytes: bytes) -> HeadPose | None:
        m = _POSE_MARKER.match(image_bytes)
        if not m:
            return HeadPose(yaw=0.0, pitch=0.0, roll=0.0)
        return HeadPose(yaw=float(m.group(1)), pitch=float(m.group(2)), roll=0.0)
