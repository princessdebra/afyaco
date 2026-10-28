"""Resolves a Tenant row's `adapter_key` to a concrete TenantAdapter instance.

Onboarding a real insurer later means: write `app/adapters/<insurer>.py`
implementing `TenantAdapter`, register it in `_ADAPTERS` below, and set that
tenant's `adapter_key`. Nothing else in the platform changes.
"""

from app.adapters.base import TenantAdapter
from app.adapters.stub import StubAdapter

_ADAPTERS: dict[str, type[TenantAdapter]] = {
    "stub": StubAdapter,
}

_instances: dict[str, TenantAdapter] = {}


def get_adapter(adapter_key: str) -> TenantAdapter:
    if adapter_key not in _ADAPTERS:
        raise ValueError(
            f"No adapter registered for key '{adapter_key}'. "
            f"Known adapters: {sorted(_ADAPTERS)}"
        )
    if adapter_key not in _instances:
        _instances[adapter_key] = _ADAPTERS[adapter_key]()
    return _instances[adapter_key]
