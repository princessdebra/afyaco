import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class TenantKind(str, enum.Enum):
    MIP = "mip"  # Medical Insurance Provider (e.g. Minet)
    INSURER = "insurer"
    TPA = "tpa"


class Tenant(IdMixin, TimestampMixin, Base):
    """A customer organisation (MIP, insurer or TPA).

    Organisational relationships are configurable rather than fixed to a single
    hierarchy (see brief §3) — this row is the isolation boundary for data,
    roles, configuration and audit access.
    """

    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[TenantKind] = mapped_column(Enum(TenantKind, name="tenant_kind"))
    # Which adapter implementation (see app.adapters.registry) resolves this
    # tenant's member/eligibility/benefits/provider/pre-auth/claims data.
    adapter_key: Mapped[str] = mapped_column(String(64), default="stub")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
