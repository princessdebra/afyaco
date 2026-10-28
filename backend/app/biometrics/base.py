"""Biometric provider abstraction for Xenova Identity Assurance (XIA).

This is the replaceable boundary the rest of XIA depends on — swapping in a
real, validated face-verification vendor later means writing one class here
and registering it (see app.biometrics.registry), not touching the services,
API routes or models. No concrete production vendor is wired up yet; only
`MockBiometricProvider` (app/biometrics/mock.py) exists, and it is NOT
biometric security — see that module's docstring.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class QualityDecision(str, Enum):
    ACCEPTABLE = "acceptable"
    REJECTED = "rejected"


class LivenessDecision(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class MatchDecision(str, Enum):
    MATCH = "match"
    NO_MATCH = "no_match"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


@dataclass
class QualityResult:
    decision: QualityDecision
    reason: str | None = None


@dataclass
class LivenessResult:
    decision: LivenessDecision
    reason: str | None = None


@dataclass
class EnrollmentReference:
    template_ref: str  # opaque; provider-defined
    template_version: str


@dataclass
class MatchResult:
    decision: MatchDecision
    score: float | None  # provider-defined scale; do not compare across providers
    threshold: float | None


@dataclass
class ProviderHealth:
    healthy: bool
    detail: str | None = None


@dataclass
class HeadPose:
    yaw: float  # degrees; sign convention is provider-specific — see implementation
    pitch: float
    roll: float


class BiometricVerificationProvider(ABC):
    """Everything a real vendor integration must implement. Each method is a
    named integration point from the product brief (§4.4); a real
    implementation calls out to the vendor's SDK/API here, with the vendor's
    own documented thresholds, licensing, and liveness/presentation-attack
    coverage, none of which this interface fabricates on the caller's behalf.
    """

    key: str

    @abstractmethod
    async def assess_capture_quality(self, image_bytes: bytes) -> QualityResult: ...

    @abstractmethod
    async def perform_liveness_check(self, image_bytes: bytes) -> LivenessResult: ...

    @abstractmethod
    async def create_enrollment_reference(self, image_bytes: bytes) -> EnrollmentReference: ...

    @abstractmethod
    async def compare_with_enrollment(self, template_ref: str, probe_image_bytes: bytes) -> MatchResult: ...

    @abstractmethod
    async def get_provider_health(self) -> ProviderHealth: ...

    @abstractmethod
    async def estimate_head_pose(self, image_bytes: bytes) -> HeadPose | None:
        """Returns None if no single face could be measured (so challenge-
        response liveness can treat that frame as unusable rather than
        guessing)."""
        ...
