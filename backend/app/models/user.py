import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class UserRole(str, enum.Enum):
    """Mirrors the user table in brief §3."""

    MEMBER = "member"
    MINET_OPS = "minet_ops"
    CLINICIAN = "clinician"
    PROVIDER_PARTICIPANT = "provider_participant"
    PHARMACY = "pharmacy"
    LABORATORY = "laboratory"
    CLAIMS_OFFICER = "claims_officer"
    TENANT_ADMIN = "tenant_admin"


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    # Globally unique, not per-tenant — login resolves the tenant FROM the
    # email, the user never picks it themselves (one person, one employer/
    # insurer, one login identity).
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"))
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Set when role == MEMBER, links the login identity to the operational member record.
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=True
    )
    # Set when role in (CLINICIAN, PROVIDER_PARTICIPANT): this login IS/represents
    # that provider row, scoping which appointments/consultations they can see
    # and act on. Left null for MINET_OPS/TENANT_ADMIN, who see across the tenant.
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True
    )
