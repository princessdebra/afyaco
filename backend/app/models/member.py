import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class MemberStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LAPSED = "lapsed"
    UNKNOWN = "unknown"


class Member(IdMixin, TimestampMixin, Base):
    """The minimum operational copy of a member/dependant resolved from the
    tenant's member API (brief §2, §4). Minet/the insurer remains the source of
    truth — this row is a cache for operational use, never for inferring cover.

    `source` + `retrieved_at` make every display explicit about provenance, per
    brief §5 ("mark cached data with source and retrieval time").
    """

    __tablename__ = "members"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    external_ref: Mapped[str] = mapped_column(String(128), index=True)  # the tenant system's member reference
    full_name: Mapped[str] = mapped_column(String(255))
    is_principal: Mapped[bool] = mapped_column(default=True)
    principal_member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=True
    )
    relationship_to_principal: Mapped[str | None] = mapped_column(String(64), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    scheme: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[MemberStatus] = mapped_column(Enum(MemberStatus, name="member_status"), default=MemberStatus.UNKNOWN)
    coverage_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    coverage_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Provenance of this cached copy — never treat as authoritative for a
    # consequential decision without rechecking the adapter (brief §5).
    source: Mapped[str] = mapped_column(String(128))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
