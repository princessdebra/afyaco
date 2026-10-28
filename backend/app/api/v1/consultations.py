import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_db_user, get_current_user
from app.models.consultation import Consultation
from app.models.user import User
from app.schemas.consultation import ConsultationOut, ConversationOut
from app.services.consultations import end_consultation, get_by_appointment, list_my_conversations, start_consultation

router = APIRouter(prefix="/consultations", tags=["consultations"])


class ConsultationStart(BaseModel):
    appointment_id: uuid.UUID


@router.post("/start", response_model=ConsultationOut)
def start(
    payload: ConsultationStart,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Consultation:
    consultation = start_consultation(
        db,
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        appointment_id=payload.appointment_id,
    )
    db.commit()
    db.refresh(consultation)
    return consultation


@router.get("/mine", response_model=list[ConversationOut])
def my_conversations(
    current: CurrentUser = Depends(get_current_user),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> list[ConversationOut]:
    return list_my_conversations(db, tenant_id=current.tenant_id, user=user, role=current.role)


@router.get("/by-appointment/{appointment_id}", response_model=ConsultationOut)
def consultation_by_appointment(
    appointment_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Consultation:
    return get_by_appointment(db, tenant_id=current.tenant_id, appointment_id=appointment_id)


@router.post("/{consultation_id}/end", response_model=ConsultationOut)
def end(
    consultation_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Consultation:
    consultation = end_consultation(
        db,
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        consultation_id=consultation_id,
    )
    db.commit()
    db.refresh(consultation)
    return consultation
