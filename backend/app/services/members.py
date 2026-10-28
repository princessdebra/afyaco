import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.adapters.base import TenantAdapter
from app.models.member import Member, MemberStatus
from app.schemas.canonical import MemberRecord


def _upsert_from_record(db: Session, tenant_id: uuid.UUID, record: MemberRecord) -> Member:
    member = (
        db.query(Member)
        .filter(Member.tenant_id == tenant_id, Member.external_ref == record.external_ref)
        .first()
    )
    if member is None:
        member = Member(tenant_id=tenant_id, external_ref=record.external_ref)
        db.add(member)

    member.full_name = record.full_name
    member.is_principal = record.is_principal
    member.relationship_to_principal = record.relationship_to_principal
    member.date_of_birth = record.date_of_birth
    member.scheme = record.scheme
    member.plan = record.plan
    member.status = MemberStatus(record.status) if record.status in MemberStatus._value2member_map_ else MemberStatus.UNKNOWN
    member.coverage_start = record.coverage_start
    member.coverage_end = record.coverage_end
    member.source = record.meta.source
    member.retrieved_at = record.meta.retrieved_at
    db.flush()
    return member


async def sync_member(db: Session, tenant_id: uuid.UUID, adapter: TenantAdapter, external_ref: str) -> Member | None:
    """Resolve a member through the tenant adapter and refresh the local
    operational copy (brief §2 "retain only the minimum operational copy",
    §5 "mark cached data with source and retrieval time").
    """
    record = await adapter.find_member(external_ref)
    if record is None:
        return None
    return _upsert_from_record(db, tenant_id, record)


def is_stale(member: Member, max_age_minutes: int = 30) -> bool:
    age = datetime.now(timezone.utc) - member.retrieved_at
    return age.total_seconds() > max_age_minutes * 60
