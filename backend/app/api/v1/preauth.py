import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.base import TenantAdapter
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, get_tenant_adapter
from app.models.preauth import PreAuthRequest
from app.schemas.preauth import PreAuthCreate, PreAuthOut
from app.services.preauth import start_preauth

router = APIRouter(prefix="/preauth", tags=["preauth"])


@router.post("", response_model=PreAuthOut, status_code=status.HTTP_201_CREATED)
async def create_preauth(
    payload: PreAuthCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    adapter: TenantAdapter = Depends(get_tenant_adapter),
) -> PreAuthRequest:
    request = await start_preauth(
        db,
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        adapter=adapter,
        member_id=payload.member_id,
        service_reference=payload.service_reference,
        service_code=payload.service_code,
        recommendation_id=payload.recommendation_id,
        appointment_id=payload.appointment_id,
        attachments=payload.attachments,
    )
    db.commit()
    db.refresh(request)
    return request


@router.get("/{preauth_id}", response_model=PreAuthOut)
def get_preauth(
    preauth_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PreAuthRequest:
    request = db.query(PreAuthRequest).filter(
        PreAuthRequest.id == preauth_id, PreAuthRequest.tenant_id == current.tenant_id
    ).first()
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pre-authorisation request not found")
    return request
