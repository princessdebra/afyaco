import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.adapters.base import TenantAdapter
from app.models.member import Member
from app.models.preauth import PreAuthRequest, PreAuthStatus
from app.services import audit


async def start_preauth(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    adapter: TenantAdapter,
    member_id: uuid.UUID,
    service_reference: str,
    service_code: str,
    recommendation_id: uuid.UUID | None,
    appointment_id: uuid.UUID | None,
    attachments: list[dict],
) -> PreAuthRequest:
    """Brief §8 "Authorisation orchestration": requirement check, request
    assembly, submission, status tracking. The actual decision engine is
    Minet's (brief §2) — reached here only through the adapter boundary.
    """
    member = db.get(Member, member_id)
    needs_preauth = await adapter.requires_preauth(member.external_ref, service_code)

    request = PreAuthRequest(
        tenant_id=tenant_id,
        member_id=member_id,
        recommendation_id=recommendation_id,
        appointment_id=appointment_id,
        service_reference=service_reference,
        attachments=attachments,
        status=PreAuthStatus.NOT_REQUIRED if not needs_preauth else PreAuthStatus.PENDING,
    )
    db.add(request)
    db.flush()

    if needs_preauth:
        result = await adapter.submit_preauth(member.external_ref, service_code, attachments)
        request.external_request_id = result.external_request_id
        request.status = PreAuthStatus(result.status)
        request.conditions = result.conditions
        request.reasons = result.reasons
        request.approved_amount = result.approved_amount
        request.validity = result.validity
        request.submitted_at = datetime.now(timezone.utc)

    audit.record(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="preauth.requested",
        resource_type="preauth_request",
        resource_id=str(request.id),
        context={"needs_preauth": needs_preauth, "service_code": service_code},
    )
    return request
