import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.member import MemberStatus


class MemberOut(BaseModel):
    id: uuid.UUID
    external_ref: str
    full_name: str
    is_principal: bool
    relationship_to_principal: str | None = None
    date_of_birth: date | None = None
    scheme: str | None
    plan: str | None
    status: MemberStatus
    coverage_start: date | None
    coverage_end: date | None
    source: str
    retrieved_at: datetime

    class Config:
        from_attributes = True


class BenefitOut(BaseModel):
    benefit: str
    limit_amount: str
    used_amount: str
    remaining_amount: str
    co_pay: str | None
    source: str
    retrieved_at: datetime
