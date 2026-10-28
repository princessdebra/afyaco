import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.adapters.base import TenantAdapter
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_db_user, get_current_user, get_tenant_adapter, require_roles
from app.models.appointment import Appointment, AppointmentStatus
from app.models.member import Member
from app.models.provider import Provider
from app.models.user import User, UserRole
from app.services import audit
from app.schemas.appointment import AppointmentCreate, AppointmentOut
from app.services.appointments import book_appointment

FACILITY_STAFF_ROLES = (UserRole.PROVIDER_PARTICIPANT, UserRole.CLINICIAN, UserRole.MINET_OPS, UserRole.TENANT_ADMIN)
# Roles scoped to only their own linked provider — ops/admin see the whole tenant.
PROVIDER_SCOPED_ROLES = (UserRole.PROVIDER_PARTICIPANT, UserRole.CLINICIAN)


class AppointmentReschedule(BaseModel):
    scheduled_at: datetime

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _require_provider_access(appointment: Appointment, current: CurrentUser, user: User) -> None:
    if current.role in PROVIDER_SCOPED_ROLES and appointment.provider_id != user.provider_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your provider's appointment")


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    payload: AppointmentCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    adapter: TenantAdapter = Depends(get_tenant_adapter),
) -> Appointment:
    provider = db.query(Provider).filter(
        Provider.id == payload.provider_id, Provider.tenant_id == current.tenant_id
    ).first()
    if provider is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not found")

    appointment = await book_appointment(
        db,
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        adapter=adapter,
        member_id=payload.member_id,
        provider_id=payload.provider_id,
        provider_external_ref=provider.external_ref,
        mode=payload.mode,
        scheduled_at=payload.scheduled_at,
        reason=payload.reason,
        idempotency_key=payload.idempotency_key,
    )
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    member_id: uuid.UUID | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Appointment]:
    query = db.query(Appointment).filter(Appointment.tenant_id == current.tenant_id)
    if member_id is not None:
        query = query.filter(Appointment.member_id == member_id)
    return query.order_by(Appointment.scheduled_at.desc()).all()


@router.get("/pending", response_model=list[AppointmentOut])
def list_pending_appointments(
    current: CurrentUser = Depends(require_roles(*FACILITY_STAFF_ROLES)),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> list[Appointment]:
    """Appointments awaiting provider confirmation — the provider-portal
    approval queue. Facility/clinician logins only see their own linked
    provider's requests; ops/admin see the whole tenant's queue.
    """
    query = db.query(Appointment).filter(
        Appointment.tenant_id == current.tenant_id, Appointment.status == AppointmentStatus.REQUESTED
    )
    if current.role in PROVIDER_SCOPED_ROLES:
        if user.provider_id is None:
            return []
        query = query.filter(Appointment.provider_id == user.provider_id)
    return query.order_by(Appointment.scheduled_at).all()


@router.get("/mine", response_model=list[AppointmentOut])
def list_my_provider_appointments(
    current: CurrentUser = Depends(require_roles(*FACILITY_STAFF_ROLES)),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> list[Appointment]:
    """Confirmed/upcoming appointments for the provider-portal's consultation
    list (where a Chat/Join Call action lives) — same scoping as /pending.
    """
    query = db.query(Appointment).filter(
        Appointment.tenant_id == current.tenant_id,
        Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.RESCHEDULED, AppointmentStatus.COMPLETED]),
    )
    if current.role in PROVIDER_SCOPED_ROLES:
        if user.provider_id is None:
            return []
        query = query.filter(Appointment.provider_id == user.provider_id)
    return query.order_by(Appointment.scheduled_at.desc()).all()


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Appointment:
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.tenant_id == current.tenant_id
    ).first()
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    return appointment


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(
    appointment_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Appointment:
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.tenant_id == current.tenant_id
    ).first()
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Appointment is already {appointment.status.value}")
    appointment.status = AppointmentStatus.CANCELLED
    db.flush()
    audit.record(
        db,
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        action="appointment.cancelled",
        resource_type="appointment",
        resource_id=str(appointment.id),
    )
    db.commit()
    db.refresh(appointment)
    return appointment


@router.post("/{appointment_id}/confirm", response_model=AppointmentOut)
def confirm_appointment(
    appointment_id: uuid.UUID,
    current: CurrentUser = Depends(require_roles(*FACILITY_STAFF_ROLES)),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> Appointment:
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.tenant_id == current.tenant_id
    ).first()
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    _require_provider_access(appointment, current, user)
    if appointment.status != AppointmentStatus.REQUESTED:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Appointment is {appointment.status.value}, not pending")

    appointment.status = AppointmentStatus.CONFIRMED
    db.flush()
    audit.record(
        db, tenant_id=current.tenant_id, actor_user_id=current.user_id,
        action="appointment.confirmed", resource_type="appointment", resource_id=str(appointment.id),
    )
    db.commit()
    db.refresh(appointment)
    return appointment


@router.post("/{appointment_id}/decline", response_model=AppointmentOut)
def decline_appointment(
    appointment_id: uuid.UUID,
    current: CurrentUser = Depends(require_roles(*FACILITY_STAFF_ROLES)),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> Appointment:
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.tenant_id == current.tenant_id
    ).first()
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    _require_provider_access(appointment, current, user)
    if appointment.status != AppointmentStatus.REQUESTED:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Appointment is {appointment.status.value}, not pending")

    appointment.status = AppointmentStatus.CANCELLED
    db.flush()
    audit.record(
        db, tenant_id=current.tenant_id, actor_user_id=current.user_id,
        action="appointment.declined", resource_type="appointment", resource_id=str(appointment.id),
    )
    db.commit()
    db.refresh(appointment)
    return appointment


@router.post("/{appointment_id}/reschedule", response_model=AppointmentOut)
async def reschedule_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentReschedule,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    adapter: TenantAdapter = Depends(get_tenant_adapter),
) -> Appointment:
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.tenant_id == current.tenant_id
    ).first()
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Appointment is already {appointment.status.value}")

    provider = db.get(Provider, appointment.provider_id)
    member = db.get(Member, appointment.member_id)
    eligibility = await adapter.check_eligibility(
        member_external_ref=member.external_ref,
        service_code="consultation",
        provider_external_ref=provider.external_ref,
        on_date=payload.scheduled_at.date().isoformat(),
    )

    previous_scheduled_at = appointment.scheduled_at
    appointment.scheduled_at = payload.scheduled_at
    appointment.status = AppointmentStatus.RESCHEDULED
    appointment.cover_confirmed = eligibility.outcome == "eligible"
    appointment.cover_check_source = eligibility.meta.source
    appointment.cover_check_at = datetime.now(timezone.utc)
    db.flush()
    audit.record(
        db,
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        action="appointment.rescheduled",
        resource_type="appointment",
        resource_id=str(appointment.id),
        context={"from": previous_scheduled_at.isoformat(), "to": payload.scheduled_at.isoformat()},
    )
    db.commit()
    db.refresh(appointment)
    return appointment
