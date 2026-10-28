import enum
import uuid

from sqlalchemy import ARRAY, Boolean, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import IdMixin, TimestampMixin


class ProviderType(str, enum.Enum):
    CLINICIAN = "clinician"
    FACILITY = "facility"
    PHARMACY = "pharmacy"
    LABORATORY = "laboratory"


class IntegrationLevel(str, enum.Enum):
    """Brief §11 — the provider's integration maturity. The journey must look the
    same to the member regardless of which level a given provider sits at."""

    DIRECT_API = "1_direct_api"
    PORTAL = "2_portal"
    ACTION_LINK = "3_action_link"
    MINET_ASSISTED = "4_minet_assisted"


class Provider(IdMixin, TimestampMixin, Base):
    """Digitised panel entry (brief §2 "Digitise provider data, eligibility,
    matching, booking and operational interaction" is Xenova's job, independent
    of how a given partner is actually integrated).
    """

    __tablename__ = "providers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    external_ref: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[ProviderType] = mapped_column(Enum(ProviderType, name="provider_type"))
    specialties: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telemedicine_capable: Mapped[bool] = mapped_column(Boolean, default=False)
    network_status: Mapped[str] = mapped_column(String(32), default="panel")  # panel | out_of_panel
    integration_level: Mapped[IntegrationLevel] = mapped_column(
        Enum(IntegrationLevel, name="integration_level"), default=IntegrationLevel.MINET_ASSISTED
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Registered facility coordinates + per-facility geofence tolerance (brief
    # §7.2) — used only as corroborating evidence for identity assurance, never
    # as proof on its own (brief §7.1). Null for non-facility provider rows
    # (individual clinicians without their own registered location).
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geofence_meters: Mapped[int | None] = mapped_column(Integer, nullable=True, default=300)
