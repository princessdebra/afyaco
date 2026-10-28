from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token, verify_password
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Local credential login. Real deployments will likely federate identity
    through each tenant's own identity provider (SSO, member portal login,
    etc.) — that's an integration concern, deferred. This issues our own JWT
    in the meantime so every other endpoint can depend on tenant-scoped auth
    today.

    The tenant is resolved FROM the account (email is globally unique), never
    chosen by the person signing in — a member doesn't get to pick which
    insurer they are.
    """
    user = db.query(User).filter(User.email == payload.email, User.is_active.is_(True)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id, Tenant.is_active.is_(True)).first()
    if tenant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This account's organisation is inactive")

    token = create_access_token(subject=str(user.id), tenant_slug=tenant.slug, role=user.role.value)
    return TokenResponse(
        access_token=token, role=user.role, full_name=user.full_name,
        tenant_slug=tenant.slug, tenant_name=tenant.name,
    )
