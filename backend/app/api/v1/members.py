import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.base import TenantAdapter
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, get_tenant_adapter, require_roles
from app.models.member import Member
from app.models.user import User, UserRole
from app.schemas.member import BenefitOut, MemberOut
from app.services.members import is_stale, sync_member

router = APIRouter(prefix="/members", tags=["members"])

STAFF_ROLES = (UserRole.PROVIDER_PARTICIPANT, UserRole.CLINICIAN, UserRole.MINET_OPS, UserRole.TENANT_ADMIN)


@router.get("/by-id/{member_id}", response_model=MemberOut)
def get_member_by_id(
    member_id: uuid.UUID,
    current: CurrentUser = Depends(require_roles(*STAFF_ROLES)),
    db: Session = Depends(get_db),
) -> Member:
    """Provider/clinician-facing lookup — e.g. resolving who a given
    appointment's patient is. Staff-only; a member can't use this to look up
    another member.
    """
    member = db.query(Member).filter(Member.id == member_id, Member.tenant_id == current.tenant_id).first()
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return member


@router.get("/me", response_model=MemberOut)
def get_my_member(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Member:
    """Resolves the logged-in member's own record (brief — every member page
    should act on whoever is actually signed in, not a hardcoded demo
    member). 404s for non-member roles or a member user with no linked row.
    """
    user = db.query(User).filter(User.id == current.user_id, User.tenant_id == current.tenant_id).first()
    if user is None or user.member_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No member record linked to this account")
    member = db.query(Member).filter(Member.id == user.member_id, Member.tenant_id == current.tenant_id).first()
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No member record linked to this account")
    return member


@router.get("/{external_ref}", response_model=MemberOut)
async def get_member(
    external_ref: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    adapter: TenantAdapter = Depends(get_tenant_adapter),
) -> Member:
    member = db.query(Member).filter(Member.tenant_id == current.tenant_id, Member.external_ref == external_ref).first()
    if member is None or is_stale(member):
        member = await sync_member(db, current.tenant_id, adapter, external_ref)
        db.commit()
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return member


@router.get("/{external_ref}/dependants", response_model=list[MemberOut])
def get_dependants(
    external_ref: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Member]:
    principal = db.query(Member).filter(Member.tenant_id == current.tenant_id, Member.external_ref == external_ref).first()
    if principal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return db.query(Member).filter(Member.principal_member_id == principal.id).order_by(Member.full_name).all()


@router.get("/{external_ref}/benefits", response_model=list[BenefitOut])
async def get_member_benefits(
    external_ref: str,
    current: CurrentUser = Depends(get_current_user),
    adapter: TenantAdapter = Depends(get_tenant_adapter),
) -> list[BenefitOut]:
    """Always calls through the adapter live — benefit balances are exactly the
    kind of consequential data brief §5 says must never be inferred from a
    stale cache.
    """
    records = await adapter.list_benefits(external_ref)
    return [
        BenefitOut(
            benefit=r.benefit,
            limit_amount=r.limit_amount,
            used_amount=r.used_amount,
            remaining_amount=r.remaining_amount,
            co_pay=r.co_pay,
            source=r.meta.source,
            retrieved_at=r.meta.retrieved_at,
        )
        for r in records
    ]
