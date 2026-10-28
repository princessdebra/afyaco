import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.adapters.base import TenantAdapter
from app.models.claim import Claim, ClaimStatus
from app.models.member import Member
from app.services import audit


async def submit_claim(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    adapter: TenantAdapter,
    member_id: uuid.UUID,
    appointment_id: uuid.UUID | None,
    preauth_id: uuid.UUID | None,
    lines: list[dict],
) -> Claim:
    """Brief §8 "Claims orchestration" + §6 step 10: link encounter, order,
    authorisation and evidence, then submit through the adapter. FAWE
    submission (brief §12) is intentionally not wired here yet — `fawe_*`
    columns stay null until that integration exists.
    """
    member = db.get(Member, member_id)

    claim = Claim(
        tenant_id=tenant_id,
        member_id=member_id,
        appointment_id=appointment_id,
        preauth_id=preauth_id,
        lines=lines,
        status=ClaimStatus.DRAFT,
    )
    db.add(claim)
    db.flush()

    result = await adapter.submit_claim(member.external_ref, lines)
    claim.external_claim_id = result.external_claim_id
    claim.status = ClaimStatus(result.status) if result.status in ClaimStatus._value2member_map_ else ClaimStatus.SUBMITTED
    claim.submitted_at = datetime.now(timezone.utc)

    audit.record(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="claim.submitted",
        resource_type="claim",
        resource_id=str(claim.id),
        context={"external_claim_id": result.external_claim_id},
    )
    return claim
