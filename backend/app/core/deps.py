import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, WebSocket, WebSocketException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.adapters.base import TenantAdapter
from app.adapters.registry import get_adapter
from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.tenant import Tenant
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass
class CurrentUser:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_slug: str
    role: UserRole


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> CurrentUser:
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials") from exc

    tenant = db.query(Tenant).filter(Tenant.slug == payload["tenant"], Tenant.is_active.is_(True)).first()
    if tenant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown or inactive tenant")

    return CurrentUser(
        user_id=uuid.UUID(payload["sub"]),
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        role=UserRole(payload["role"]),
    )


def get_current_db_user(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Resolves the full User row for endpoints that need `member_id`/
    `provider_id` — the JWT only carries what get_current_user exposes."""
    user = db.query(User).filter(User.id == current.user_id, User.tenant_id == current.tenant_id).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def get_ws_current_user(websocket: WebSocket, db: Session) -> CurrentUser:
    """WebSocket equivalent of get_current_user — browsers can't set a
    custom Authorization header on a WS handshake, so the token travels as
    a query param instead (?token=...), same JWT either way.
    """
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token") from exc

    tenant = db.query(Tenant).filter(Tenant.slug == payload["tenant"], Tenant.is_active.is_(True)).first()
    if tenant is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Unknown or inactive tenant")

    return CurrentUser(
        user_id=uuid.UUID(payload["sub"]),
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        role=UserRole(payload["role"]),
    )


def require_roles(*roles: UserRole):
    def _check(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this role")
        return current

    return _check


def get_tenant_adapter(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> TenantAdapter:
    tenant = db.get(Tenant, current.tenant_id)
    return get_adapter(tenant.adapter_key)


def get_biometric_provider():
    from app.biometrics.registry import get_provider

    return get_provider()
