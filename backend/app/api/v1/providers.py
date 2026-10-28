import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models.provider import Provider, ProviderType
from app.schemas.provider import ProviderOut

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderOut])
def list_providers(
    type: ProviderType | None = None,
    specialty: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Provider]:
    """Digitised panel data (brief §2) — this is the platform's own cache, not a
    live adapter call, since provider search doesn't carry the same
    consequential-decision risk as eligibility/benefits (brief §5).
    """
    query = db.query(Provider).filter(Provider.tenant_id == current.tenant_id, Provider.is_active.is_(True))
    if type is not None:
        query = query.filter(Provider.type == type)
    if specialty:
        query = query.filter(Provider.specialties.any(specialty))
    return query.order_by(Provider.name).all()


@router.get("/{provider_id}", response_model=ProviderOut)
def get_provider(
    provider_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Provider:
    return db.query(Provider).filter(Provider.id == provider_id, Provider.tenant_id == current.tenant_id).first()
