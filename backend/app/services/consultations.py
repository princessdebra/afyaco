import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentMode, AppointmentStatus
from app.models.chat import ChatMessage, ChatSenderRole
from app.models.consultation import Consultation, ConsultationStatus
from app.models.member import Member
from app.models.provider import Provider
from app.models.user import User, UserRole
from app.services import audit

PROVIDER_SCOPED_ROLES = (UserRole.PROVIDER_PARTICIPANT, UserRole.CLINICIAN)


def start_consultation(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    appointment_id: uuid.UUID,
) -> Consultation:
    """Brief §13 safety gate: a telemedicine session cannot start until consent,
    identity and location are recorded. There's no real video provider wired up
    (deferred integration work) — `session_ref` is a local placeholder a video
    SDK's session id would replace once one is chosen.
    """
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.tenant_id == tenant_id
    ).first()
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    if appointment.mode != AppointmentMode.TELEMEDICINE:
        raise HTTPException(status.HTTP_409_CONFLICT, "This appointment is not a telemedicine consultation")
    if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Appointment is {appointment.status.value}")

    consultation = db.query(Consultation).filter(Consultation.appointment_id == appointment_id).first()
    if consultation is None:
        consultation = Consultation(tenant_id=tenant_id, appointment_id=appointment_id)
        db.add(consultation)
        db.flush()

    if consultation.status == ConsultationStatus.IN_PROGRESS:
        return consultation
    if consultation.status in (ConsultationStatus.COMPLETED, ConsultationStatus.CANCELLED):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Consultation already {consultation.status.value}")

    now = datetime.now(timezone.utc)
    consultation.status = ConsultationStatus.IN_PROGRESS
    consultation.consent_captured_at = now
    consultation.identity_verified = True
    consultation.location_confirmed = True
    consultation.started_at = now
    consultation.session_ref = f"demo-{secrets.token_hex(8)}"
    db.flush()

    audit.record(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="consultation.started",
        resource_type="consultation",
        resource_id=str(consultation.id),
    )
    return consultation


def end_consultation(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    consultation_id: uuid.UUID,
) -> Consultation:
    consultation = db.query(Consultation).filter(
        Consultation.id == consultation_id, Consultation.tenant_id == tenant_id
    ).first()
    if consultation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consultation not found")
    if consultation.status != ConsultationStatus.IN_PROGRESS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Consultation is {consultation.status.value}, not in progress")

    consultation.status = ConsultationStatus.COMPLETED
    consultation.ended_at = datetime.now(timezone.utc)
    db.flush()

    appointment = db.get(Appointment, consultation.appointment_id)
    if appointment is not None and appointment.status not in (AppointmentStatus.CANCELLED,):
        appointment.status = AppointmentStatus.COMPLETED

    audit.record(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="consultation.ended",
        resource_type="consultation",
        resource_id=str(consultation.id),
    )
    return consultation


def get_by_appointment(db: Session, *, tenant_id: uuid.UUID, appointment_id: uuid.UUID) -> Consultation:
    """Fetches an existing consultation regardless of status — unlike
    start_consultation, never tries to (re)activate one. Lets a completed/
    past conversation still be opened and read, or continued, from the
    chat inbox without the 409 start_consultation gives for an ended one.
    """
    consultation = db.query(Consultation).filter(
        Consultation.appointment_id == appointment_id, Consultation.tenant_id == tenant_id
    ).first()
    if consultation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No consultation for this appointment yet")
    return consultation


def list_my_conversations(db: Session, *, tenant_id: uuid.UUID, user: User, role: UserRole) -> list[dict]:
    """Backs the chat inbox's left panel — every consultation this user has
    been part of, newest activity first, with an unread count and last
    message preview. Scoped the same way as appointments/claims: a member
    sees their own threads, a clinician/facility login sees threads tied to
    their linked provider.
    """
    query = db.query(Consultation, Appointment).join(Appointment, Consultation.appointment_id == Appointment.id).filter(
        Consultation.tenant_id == tenant_id
    )
    if role == UserRole.MEMBER:
        if user.member_id is None:
            return []
        query = query.filter(Appointment.member_id == user.member_id)
    elif role in PROVIDER_SCOPED_ROLES:
        if user.provider_id is None:
            return []
        query = query.filter(Appointment.provider_id == user.provider_id)
    # ops/admin: no extra filter — tenant-wide visibility.

    rows = query.all()
    my_sender_role = ChatSenderRole.MEMBER if role == UserRole.MEMBER else ChatSenderRole.CLINICIAN

    out = []
    for consultation, appointment in rows:
        if role == UserRole.MEMBER:
            provider = db.get(Provider, appointment.provider_id)
            counterpart_name = provider.name if provider else "Provider"
        else:
            member = db.get(Member, appointment.member_id)
            counterpart_name = member.full_name if member else "Member"

        last_message = (
            db.query(ChatMessage)
            .filter(ChatMessage.consultation_id == consultation.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        unread_count = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.consultation_id == consultation.id,
                ChatMessage.sender_role != my_sender_role,
                ChatMessage.read_at.is_(None),
            )
            .count()
        )
        out.append({
            "consultation_id": consultation.id,
            "appointment_id": appointment.id,
            "counterpart_name": counterpart_name,
            "mode": appointment.mode,
            "status": consultation.status,
            "last_message": last_message.body if last_message else None,
            "last_message_at": last_message.created_at if last_message else consultation.created_at,
            "unread_count": unread_count,
        })

    out.sort(key=lambda c: c["last_message_at"], reverse=True)
    return out
