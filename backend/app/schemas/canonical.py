"""The canonical Xenova model (brief §4): the shape every tenant adapter maps
its own APIs into. Business logic and routers only ever see these types —
never a tenant's native response shape — so a new tenant is a new adapter, not
a change to the rest of the platform.
"""

from datetime import date, datetime

from pydantic import BaseModel


class SourceMeta(BaseModel):
    source: str  # e.g. "minet-member-api"
    retrieved_at: datetime
    rule_version: str | None = None
    correlation_id: str | None = None


class MemberRecord(BaseModel):
    external_ref: str
    full_name: str
    is_principal: bool
    principal_external_ref: str | None = None
    relationship_to_principal: str | None = None
    date_of_birth: date | None = None
    scheme: str | None = None
    plan: str | None = None
    status: str
    coverage_start: date | None = None
    coverage_end: date | None = None
    meta: SourceMeta


class EligibilityResult(BaseModel):
    outcome: str  # eligible | not_eligible | review
    reason: str | None = None
    network: str | None = None
    member_responsibility: str | None = None
    meta: SourceMeta


class BenefitRecord(BaseModel):
    benefit: str
    limit_amount: str
    used_amount: str
    remaining_amount: str
    exclusions: list[str] = []
    co_pay: str | None = None
    requires_referral: bool = False
    requires_preauth: bool = False
    meta: SourceMeta


class ProviderRecord(BaseModel):
    external_ref: str
    name: str
    type: str  # clinician | facility | pharmacy | laboratory
    specialties: list[str] = []
    location: str | None = None
    network_status: str = "panel"
    telemedicine_capable: bool = False
    effective_from: date | None = None
    effective_to: date | None = None
    meta: SourceMeta


class PreAuthResult(BaseModel):
    external_request_id: str
    status: str  # pending | info_requested | approved | denied
    conditions: str | None = None
    reasons: str | None = None
    approved_amount: str | None = None
    validity: str | None = None
    meta: SourceMeta


class ClaimResult(BaseModel):
    external_claim_id: str
    status: str
    claimed_amount: str | None = None
    covered_amount: str | None = None
    member_amount: str | None = None
    reasons: str | None = None
    payment_status: str | None = None
    meta: SourceMeta


class NotificationRequest(BaseModel):
    channel: str  # sms | email | push | whatsapp
    template: str
    purpose: str
    recipient_ref: str
    context: dict = {}
