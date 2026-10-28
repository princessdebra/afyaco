import uuid

from pydantic import BaseModel

from app.models.provider import IntegrationLevel, ProviderType


class ProviderOut(BaseModel):
    id: uuid.UUID
    external_ref: str
    name: str
    type: ProviderType
    specialties: list[str]
    location: str | None
    telemedicine_capable: bool
    network_status: str
    integration_level: IntegrationLevel
    latitude: float | None
    longitude: float | None

    class Config:
        from_attributes = True
