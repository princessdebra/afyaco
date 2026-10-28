import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.base import TenantAdapter
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_db_user, get_current_user, get_tenant_adapter, require_roles
from app.models.appointment import Appointment
from app.models.claim import Claim
from app.models.user import User, UserRole
from app.schemas.claim import ClaimCreate, ClaimOut
from app.services.claims import submit_claim

router = APIRouter(prefix="/claims", tags=["claims"])

FACILITY_STAFF_ROLES = (UserRole.PROVIDER_PARTICIPANT, UserRole.CLINICIAN, UserRole.MINET_OPS, UserRole.TENANT_ADMIN)
PROVIDER_SCOPED_ROLES = (UserRole.PROVIDER_PARTICIPANT, UserRole.CLINICIAN)


@router.post("", response_model=ClaimOut, status_code=status.HTTP_201_CREATED)
async def create_claim(
    payload: ClaimCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    adapter: TenantAdapter = Depends(get_tenant_adapter),
) -> Claim:
    claim = await submit_claim(
        db,
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        adapter=adapter,
        member_id=payload.member_id,
        appointment_id=payload.appointment_id,
        preauth_id=payload.preauth_id,
        lines=payload.lines,
    )
    db.commit()
    db.refresh(claim)
    return claim


@router.get("", response_model=list[ClaimOut])
def list_claims(
    member_id: uuid.UUID | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Claim]:
    query = db.query(Claim).filter(Claim.tenant_id == current.tenant_id)
    if member_id is not None:
        query = query.filter(Claim.member_id == member_id)
    return query.order_by(Claim.created_at.desc()).all()


@router.get("/mine", response_model=list[ClaimOut])
def list_my_patients_claims(
    current: CurrentUser = Depends(require_roles(*FACILITY_STAFF_ROLES)),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> list[Claim]:
    """Claims belonging to members this provider has an appointment history
    with — every claim of theirs, not just ones tied to a visit with this
    provider specifically. Facility/clinician logins are scoped to their own
    linked provider; ops/admin see the whole tenant.
    """
    member_ids_query = db.query(Appointment.member_id).filter(Appointment.tenant_id == current.tenant_id)
    if current.role in PROVIDER_SCOPED_ROLES:
        if user.provider_id is None:
            return []
        member_ids_query = member_ids_query.filter(Appointment.provider_id == user.provider_id)
    member_ids = {row[0] for row in member_ids_query.distinct()}
    if not member_ids:
        return []
    return (
        db.query(Claim)
        .filter(Claim.tenant_id == current.tenant_id, Claim.member_id.in_(member_ids))
        .order_by(Claim.created_at.desc())
        .all()
    )


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(
    claim_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Claim:
    claim = db.query(Claim).filter(Claim.id == claim_id, Claim.tenant_id == current.tenant_id).first()
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    return claim
