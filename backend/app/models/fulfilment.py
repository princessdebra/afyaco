import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class FulfilmentKind(str, enum.Enum):
    PHARMACY = "pharmacy"
    LABORATORY = "laboratory"


class FulfilmentStatus(str, enum.Enum):
    PLACED = "placed"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    RESULT_READY = "result_ready"  # laboratory
    DISPENSED = "dispensed"  # pharmacy
    CANCELLED = "cancelled"


class FulfilmentOrder(IdMixin, TimestampMixin, Base):
    """Brief §9/§10 pharmacy & laboratory coordination: order, track status,
    link to claim/FAWE — without rebuilding inventory, POS or LIS. Actually
    submitting to a partner pharmacy/lab system is integration work (deferred);
    this table tracks the local workflow and status regardless of how a given
    partner is eventually wired up (brief §11 integration levels).
    """

    __tablename__ = "fulfilment_orders"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id"), index=True)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinical_recommendations.id"), index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("providers.id"), index=True)
    preauth_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("preauth_requests.id"), nullable=True
    )

    kind: Mapped[FulfilmentKind] = mapped_column(Enum(FulfilmentKind, name="fulfilment_kind"))
    status: Mapped[FulfilmentStatus] = mapped_column(
        Enum(FulfilmentStatus, name="fulfilment_status"), default=FulfilmentStatus.PLACED
    )
    external_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)  # pointer to secured result document
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
