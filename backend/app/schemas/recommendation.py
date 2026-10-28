import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.consultation import RecommendationKind
from app.models.fulfilment import FulfilmentStatus


class FulfilmentOut(BaseModel):
    status: FulfilmentStatus
    provider_name: str | None
    external_order_id: str | None
    result_ref: str | None
    fulfilled_at: datetime | None


class RecommendationOut(BaseModel):
    id: uuid.UUID
    kind: RecommendationKind
    details: dict
    requires_preauth: bool | None
    created_at: datetime
    fulfilment: FulfilmentOut | None

    class Config:
        from_attributes = True
