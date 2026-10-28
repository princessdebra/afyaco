import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class AppointmentMode(str, enum.Enum):
    TELEMEDICINE = "telemedicine"
    PHYSICAL = "physical"


class AppointmentStatus(str, enum.Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    COMPLETED = "completed"


class Appointment(IdMixin, TimestampMixin, Base):
    """Brief §8 "Appointments" module — booking lifecycle. Eligibility/benefit
    validation (brief §7) happens through the adapter layer at booking time and
    is recorded here as a snapshot, not re-derived from this row later.
    """

    __tablename__ = "appointments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id"), index=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("providers.id"), index=True)
    mode: Mapped[AppointmentMode] = mapped_column(Enum(AppointmentMode, name="appointment_mode"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status"), default=AppointmentStatus.REQUESTED
    )
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Snapshot of the eligibility/benefit check performed at booking time
    # (brief §7 "before a consultation"). Idempotency key guards against
    # duplicate bookings on retry (brief §5).
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    cover_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    cover_check_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cover_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Set once the 15-minutes-before reminder has fired (app/services/reminders.py)
    # — guards against re-notifying every time the scheduler loop ticks.
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
