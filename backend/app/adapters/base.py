"""Adapter interface: the boundary between the platform and each tenant's (MIP /
insurer / TPA) own systems (brief §4). A new insurer is onboarded by writing one
class per interface below and registering it — see app.adapters.registry — not
by changing routers, services or models.

Every method here is where real integration work happens later (HTTP calls to
the insurer's member/eligibility/benefits/provider-panel/pre-auth/claims APIs).
Per the current scope, only `StubAdapter` (app.adapters.stub) exists — it
returns canonical-shaped mock data so the rest of the platform can be built and
tested against this interface today. No concrete insurer client is implemented
yet; that is deliberately deferred.
"""

from abc import ABC, abstractmethod

from app.schemas.canonical import (
    BenefitRecord,
    ClaimResult,
    EligibilityResult,
    MemberRecord,
    NotificationRequest,
    PreAuthResult,
    ProviderRecord,
)


class MemberAdapter(ABC):
    @abstractmethod
    async def find_member(self, external_ref: str) -> MemberRecord | None: ...

    @abstractmethod
    async def list_dependants(self, principal_external_ref: str) -> list[MemberRecord]: ...


class EligibilityAdapter(ABC):
    @abstractmethod
    async def check_eligibility(
        self, member_external_ref: str, service_code: str, provider_external_ref: str, on_date: str
    ) -> EligibilityResult: ...


class BenefitsAdapter(ABC):
    @abstractmethod
    async def get_benefit(self, member_external_ref: str, benefit_code: str) -> BenefitRecord: ...

    @abstractmethod
    async def list_benefits(self, member_external_ref: str) -> list[BenefitRecord]: ...


class ProviderPanelAdapter(ABC):
    @abstractmethod
    async def search_providers(
        self, service_code: str | None = None, specialty: str | None = None, location: str | None = None
    ) -> list[ProviderRecord]: ...


class PreAuthAdapter(ABC):
    @abstractmethod
    async def requires_preauth(self, member_external_ref: str, service_code: str) -> bool: ...

    @abstractmethod
    async def submit_preauth(
        self, member_external_ref: str, service_code: str, attachments: list[dict]
    ) -> PreAuthResult: ...

    @abstractmethod
    async def get_preauth_status(self, external_request_id: str) -> PreAuthResult: ...


class ClaimsAdapter(ABC):
    @abstractmethod
    async def submit_claim(self, member_external_ref: str, lines: list[dict]) -> ClaimResult: ...

    @abstractmethod
    async def get_claim_status(self, external_claim_id: str) -> ClaimResult: ...


class NotificationAdapter(ABC):
    @abstractmethod
    async def send(self, request: NotificationRequest) -> str:  # returns delivery/correlation id
        ...


class TenantAdapter(
    MemberAdapter,
    EligibilityAdapter,
    BenefitsAdapter,
    ProviderPanelAdapter,
    PreAuthAdapter,
    ClaimsAdapter,
    NotificationAdapter,
    ABC,
):
    """Everything a tenant must provide. A real insurer adapter composes HTTP
    clients per interface; FAWE is deliberately not part of this interface —
    see app.adapters.base module docstring and brief §12 (kept as its own,
    still-unimplemented integration point rather than bolted onto this one).
    """

    key: str
