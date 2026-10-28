"""Deterministic in-memory adapter used until a real tenant integration exists.

Every value returned here is clearly fabricated (meta.source starts with
"stub:") so nothing from this class can be mistaken for an authoritative
response once real adapters land. It lets the rest of the platform (booking,
consultations, pre-auth/claims workflow, audit) be built and exercised end to
end today without any external integration work.
"""

from datetime import date, datetime, timezone

from app.adapters.base import TenantAdapter
from app.schemas.canonical import (
    BenefitRecord,
    ClaimResult,
    EligibilityResult,
    MemberRecord,
    NotificationRequest,
    PreAuthResult,
    ProviderRecord,
    SourceMeta,
)


def _meta(source_suffix: str) -> SourceMeta:
    return SourceMeta(source=f"stub:{source_suffix}", retrieved_at=datetime.now(timezone.utc), rule_version="stub-0")


_MEMBERS: dict[str, MemberRecord] = {
    "MNT-0942-SC8591": MemberRecord(
        external_ref="MNT-0942-SC8591",
        full_name="John Mwangi",
        is_principal=True,
        scheme="Minet Comprehensive Executive",
        plan="POL-MIN-884270",
        status="active",
        coverage_start=date(2026, 1, 1),
        coverage_end=date(2026, 12, 31),
        meta=_meta("member-api"),
    ),
}


class StubAdapter(TenantAdapter):
    key = "stub"

    async def find_member(self, external_ref: str) -> MemberRecord | None:
        return _MEMBERS.get(external_ref)

    async def list_dependants(self, principal_external_ref: str) -> list[MemberRecord]:
        return [m for m in _MEMBERS.values() if m.principal_external_ref == principal_external_ref]

    async def check_eligibility(
        self, member_external_ref: str, service_code: str, provider_external_ref: str, on_date: str
    ) -> EligibilityResult:
        eligible = member_external_ref in _MEMBERS
        return EligibilityResult(
            outcome="eligible" if eligible else "not_eligible",
            reason=None if eligible else "member not found in stub directory",
            network="panel",
            member_responsibility="KES 0",
            meta=_meta("eligibility-api"),
        )

    async def get_benefit(self, member_external_ref: str, benefit_code: str) -> BenefitRecord:
        return BenefitRecord(
            benefit=benefit_code,
            limit_amount="KES 198,000",
            used_amount="KES 120,000",
            remaining_amount="KES 78,000",
            co_pay="KES 0",
            meta=_meta("benefits-api"),
        )

    async def list_benefits(self, member_external_ref: str) -> list[BenefitRecord]:
        return [
            await self.get_benefit(member_external_ref, "outpatient"),
            await self.get_benefit(member_external_ref, "inpatient"),
        ]

    async def search_providers(
        self, service_code: str | None = None, specialty: str | None = None, location: str | None = None
    ) -> list[ProviderRecord]:
        return [
            ProviderRecord(
                external_ref="PRV-0001",
                name="Dr. Amina Njoroge",
                type="clinician",
                specialties=["General Physician"],
                location="Nairobi Health Labs",
                telemedicine_capable=True,
                meta=_meta("provider-panel-api"),
            )
        ]

    async def requires_preauth(self, member_external_ref: str, service_code: str) -> bool:
        return service_code in {"mri", "specialist_consultation"}

    async def submit_preauth(
        self, member_external_ref: str, service_code: str, attachments: list[dict]
    ) -> PreAuthResult:
        return PreAuthResult(
            external_request_id=f"stub-preauth-{member_external_ref}-{service_code}",
            status="pending",
            meta=_meta("preauth-api"),
        )

    async def get_preauth_status(self, external_request_id: str) -> PreAuthResult:
        return PreAuthResult(external_request_id=external_request_id, status="pending", meta=_meta("preauth-api"))

    async def submit_claim(self, member_external_ref: str, lines: list[dict]) -> ClaimResult:
        return ClaimResult(
            external_claim_id=f"stub-claim-{member_external_ref}",
            status="submitted",
            meta=_meta("claims-api"),
        )

    async def get_claim_status(self, external_claim_id: str) -> ClaimResult:
        return ClaimResult(external_claim_id=external_claim_id, status="in_review", meta=_meta("claims-api"))

    async def send(self, request: NotificationRequest) -> str:
        return f"stub-notification-{request.recipient_ref}"
