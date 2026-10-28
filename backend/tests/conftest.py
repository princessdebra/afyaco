import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.db import Base, SessionLocal, engine
from app.models.member import Member, MemberStatus
from app.models.provider import Provider, ProviderType
from app.models.tenant import Tenant, TenantKind
from app.models.user import User, UserRole


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    """Tests run against a real Postgres database (set DATABASE_URL to a
    throwaway test database before running) — the models use Postgres-only
    types (UUID, ARRAY), so SQLite is not an option here.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def tenant(db: Session) -> Tenant:
    t = Tenant(slug=f"test-{uuid.uuid4().hex[:8]}", name="Test Tenant", kind=TenantKind.MIP, adapter_key="stub")
    db.add(t)
    db.commit()
    return t


@pytest.fixture()
def member(db: Session, tenant: Tenant) -> Member:
    m = Member(
        tenant_id=tenant.id,
        external_ref=f"MEM-{uuid.uuid4().hex[:8]}",
        full_name="Test Member",
        is_principal=True,
        status=MemberStatus.ACTIVE,
        source="test",
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(m)
    db.commit()
    return m


@pytest.fixture()
def other_member(db: Session, tenant: Tenant) -> Member:
    m = Member(
        tenant_id=tenant.id,
        external_ref=f"MEM-{uuid.uuid4().hex[:8]}",
        full_name="Other Member",
        is_principal=True,
        status=MemberStatus.ACTIVE,
        source="test",
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(m)
    db.commit()
    return m


@pytest.fixture()
def facility(db: Session, tenant: Tenant) -> Provider:
    p = Provider(
        tenant_id=tenant.id,
        external_ref=f"FAC-{uuid.uuid4().hex[:8]}",
        name="Test Hospital",
        type=ProviderType.FACILITY,
        specialties=["Hospital"],
        latitude=-1.2833,
        longitude=36.8167,
        geofence_meters=300,
    )
    db.add(p)
    db.commit()
    return p


@pytest.fixture()
def other_facility(db: Session, tenant: Tenant) -> Provider:
    p = Provider(
        tenant_id=tenant.id,
        external_ref=f"FAC-{uuid.uuid4().hex[:8]}",
        name="Other Hospital",
        type=ProviderType.FACILITY,
        specialties=["Hospital"],
        latitude=-1.3,
        longitude=36.75,
        geofence_meters=300,
    )
    db.add(p)
    db.commit()
    return p


@pytest.fixture()
def staff_user(db: Session, tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id,
        email=f"staff-{uuid.uuid4().hex[:8]}@test.local",
        password_hash="x",
        role=UserRole.PROVIDER_PARTICIPANT,
        full_name="Test Staff",
    )
    db.add(u)
    db.commit()
    return u
