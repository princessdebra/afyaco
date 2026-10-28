import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.chat import ChatMessage, ChatSenderRole
from app.models.consultation import Consultation
from app.models.user import User, UserRole

STAFF_ROLES = (UserRole.PROVIDER_PARTICIPANT, UserRole.CLINICIAN, UserRole.MINET_OPS, UserRole.TENANT_ADMIN)


def authorize_consultation_access(
    db: Session, *, tenant_id: uuid.UUID, user: User, role: UserRole, consultation_id: uuid.UUID
) -> tuple[Consultation, Appointment]:
    """Only the member who booked it, the clinician/facility it's booked
    with, or tenant ops/admin may read or post to a consultation's chat.
    """
    consultation = db.query(Consultation).filter(
        Consultation.id == consultation_id, Consultation.tenant_id == tenant_id
    ).first()
    if consultation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consultation not found")
    appointment = db.get(Appointment, consultation.appointment_id)
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")

    if role == UserRole.MEMBER:
        if user.member_id != appointment.member_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your consultation")
    elif role in (UserRole.PROVIDER_PARTICIPANT, UserRole.CLINICIAN):
        if user.provider_id != appointment.provider_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your consultation")
    elif role not in (UserRole.MINET_OPS, UserRole.TENANT_ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")

    return consultation, appointment


def sender_role_for(role: UserRole) -> ChatSenderRole:
    return ChatSenderRole.MEMBER if role == UserRole.MEMBER else ChatSenderRole.CLINICIAN


def resolve_counterpart_user_ids(
    db: Session, *, tenant_id: uuid.UUID, appointment: Appointment, sender_role: ChatSenderRole
) -> list[uuid.UUID]:
    """Who should be notified about a message — the other side of the
    conversation. A message FROM the member goes TO whoever's linked to the
    provider; a message FROM the clinician side goes TO the member's login.
    """
    if sender_role == ChatSenderRole.MEMBER:
        users = db.query(User).filter(User.tenant_id == tenant_id, User.provider_id == appointment.provider_id).all()
    else:
        users = db.query(User).filter(User.tenant_id == tenant_id, User.member_id == appointment.member_id).all()
    return [u.id for u in users]


def list_messages(db: Session, consultation_id: uuid.UUID) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.consultation_id == consultation_id)
        .order_by(ChatMessage.created_at)
        .all()
    )


def create_message(
    db: Session, *, tenant_id: uuid.UUID, consultation_id: uuid.UUID, sender_user_id: uuid.UUID,
    sender_role: ChatSenderRole, body: str,
) -> ChatMessage:
    message = ChatMessage(
        tenant_id=tenant_id,
        consultation_id=consultation_id,
        sender_user_id=sender_user_id,
        sender_role=sender_role,
        body=body,
    )
    db.add(message)
    db.flush()
    return message


def mark_read(db: Session, *, consultation_id: uuid.UUID, reader_role: ChatSenderRole) -> int:
    """Marks every message NOT sent by the reader as read. Returns how many
    were newly marked, so the caller can skip an empty broadcast.
    """
    unread = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.consultation_id == consultation_id,
            ChatMessage.sender_role != reader_role,
            ChatMessage.read_at.is_(None),
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    for m in unread:
        m.read_at = now
    db.flush()
    return len(unread)
