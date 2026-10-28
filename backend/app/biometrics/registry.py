from app.biometrics.base import BiometricVerificationProvider
from app.biometrics.mock import MockBiometricProvider
from app.core.config import settings

_instance: BiometricVerificationProvider | None = None


def get_provider() -> BiometricVerificationProvider:
    """Resolves the configured biometric provider.

    Fails startup rather than silently serving the mock provider under a real
    deployment — "Do not fall back to a mock provider in production"
    (product brief §15). `opensource_cv` imports torch/insightface lazily, on
    first use, so the mock-only default install never needs those heavy deps.
    """
    global _instance
    key = settings.biometric_provider_key
    if key == "mock" and settings.environment == "production":
        raise RuntimeError(
            "biometric_provider_key is 'mock' but environment is 'production'. "
            "A real BiometricVerificationProvider must be configured."
        )
    if _instance is not None and _instance.key == key:
        return _instance

    if key == "mock":
        _instance = MockBiometricProvider()
    elif key == "opensource_cv":
        from app.biometrics.opensource_cv import OpenSourceCvProvider

        _instance = OpenSourceCvProvider()
    else:
        raise ValueError(f"No biometric provider registered for key '{key}'. Known: ['mock', 'opensource_cv']")
    return _instance
