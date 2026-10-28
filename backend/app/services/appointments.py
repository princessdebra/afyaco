import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.base import TenantAdapter
from app.models.appointment import Appointment
from app.models.member import Member
from app.services import audit


async def book_appointment(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    adapter: TenantAdapter,
    member_id: uuid.UUID,
    provider_id: uuid.UUID,
    provider_external_ref: str,
    mode: str,
    scheduled_at: datetime,
    reason: str | None,
    idempotency_key: str,
) -> Appointment:
    """Brief §6 steps 2-5: confirm active cover and the consultation benefit
    before presenting/booking as covered, then reserve the appointment.
    Idempotency key prevents duplicate bookings on client retry (brief §5).
    """
    existing = db.query(Appointment).filter(Appointment.idempotency_key == idempotency_key).first()
    if existing is not None:
        return existing

    member = db.get(Member, member_id)
    eligibility = await adapter.check_eligibility(
        member_external_ref=member.external_ref,
        service_code="consultation",
        provider_external_ref=provider_external_ref,
        on_date=scheduled_at.date().isoformat(),
    )
    cover_confirmed = eligibility.outcome == "eligible"

    appointment = Appointment(
        tenant_id=tenant_id,
        member_id=member_id,
        provider_id=provider_id,
        mode=mode,
        scheduled_at=scheduled_at,
        reason=reason,
        idempotency_key=idempotency_key,
        cover_confirmed=cover_confirmed,
        cover_check_source=eligibility.meta.source,
        cover_check_at=datetime.now(timezone.utc),
    )
    db.add(appointment)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return db.query(Appointment).filter(Appointment.idempotency_key == idempotency_key).first()

    audit.record(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="appointment.booked",
        resource_type="appointment",
        resource_id=str(appointment.id),
        context={"cover_confirmed": cover_confirmed, "eligibility_outcome": eligibility.outcome},
    )
    return appointment
