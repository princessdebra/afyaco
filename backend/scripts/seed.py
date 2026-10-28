"""Bootstraps demo data equivalent to the frontend's old src/data/mock.js, so
every page can be switched from mock data to real API calls against the same
member. Idempotent — safe to re-run.

Run with: python scripts/seed.py
"""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.appointment import Appointment, AppointmentMode, AppointmentStatus
from app.models.claim import Claim, ClaimStatus
from app.models.consultation import ClinicalRecommendation, Consultation, ConsultationStatus, RecommendationKind
from app.models.fulfilment import FulfilmentKind, FulfilmentOrder, FulfilmentStatus
from app.models.member import Member, MemberStatus
from app.models.provider import IntegrationLevel, Provider, ProviderType
from app.models.tenant import Tenant, TenantKind
from app.models.user import User, UserRole

MEMBER_REF = "MNT-0942-SC8591"


def get_or_create_provider(db, tenant_id, external_ref, **kwargs) -> Provider:
    p = db.query(Provider).filter(Provider.tenant_id == tenant_id, Provider.external_ref == external_ref).first()
    if p is None:
        p = Provider(tenant_id=tenant_id, external_ref=external_ref, **kwargs)
        db.add(p)
        db.flush()
        print(f"  provider: {p.name}")
    return p


def get_or_create_dependant(db, tenant_id, principal, external_ref, **kwargs) -> Member:
    m = db.query(Member).filter(Member.tenant_id == tenant_id, Member.external_ref == external_ref).first()
    if m is None:
        m = Member(
            tenant_id=tenant_id,
            external_ref=external_ref,
            is_principal=False,
            principal_member_id=principal.id,
            scheme=principal.scheme,
            plan=principal.plan,
            source="seed:scripts/seed.py",
            retrieved_at=datetime.now(timezone.utc),
            **kwargs,
        )
        db.add(m)
        db.flush()
        print(f"  dependant: {m.full_name}")
    return m


def get_or_create_appointment(db, tenant_id, member_id, provider_id, idempotency_key, **kwargs) -> Appointment:
    a = db.query(Appointment).filter(Appointment.idempotency_key == idempotency_key).first()
    if a is None:
        a = Appointment(
            tenant_id=tenant_id,
            member_id=member_id,
            provider_id=provider_id,
            idempotency_key=idempotency_key,
            **kwargs,
        )
        db.add(a)
        db.flush()
        print(f"  appointment: {idempotency_key}")
    return a


def get_or_create_consultation(db, tenant_id, appointment_id, **kwargs) -> Consultation:
    c = db.query(Consultation).filter(Consultation.appointment_id == appointment_id).first()
    if c is None:
        c = Consultation(tenant_id=tenant_id, appointment_id=appointment_id, **kwargs)
        db.add(c)
        db.flush()
    return c


def get_or_create_recommendation(db, tenant_id, member_id, consultation_id, kind, details, **kwargs) -> ClinicalRecommendation:
    candidates = (
        db.query(ClinicalRecommendation)
        .filter(ClinicalRecommendation.consultation_id == consultation_id, ClinicalRecommendation.kind == kind)
        .all()
    )
    existing = next((c for c in candidates if c.details.get("ref") == details.get("ref")), None)
    if existing is None:
        existing = ClinicalRecommendation(
            tenant_id=tenant_id, member_id=member_id, consultation_id=consultation_id, kind=kind, details=details, **kwargs
        )
        db.add(existing)
        db.flush()
        print(f"  recommendation ({kind.value}): {details.get('ref')}")
    return existing


def get_or_create_order(db, tenant_id, member_id, recommendation_id, provider_id, kind, **kwargs) -> FulfilmentOrder:
    existing = db.query(FulfilmentOrder).filter(FulfilmentOrder.recommendation_id == recommendation_id).first()
    if existing is None:
        existing = FulfilmentOrder(
            tenant_id=tenant_id,
            member_id=member_id,
            recommendation_id=recommendation_id,
            provider_id=provider_id,
            kind=kind,
            **kwargs,
        )
        db.add(existing)
        db.flush()
    return existing


def get_or_create_claim(db, tenant_id, member_id, external_claim_id, **kwargs) -> Claim:
    existing = db.query(Claim).filter(Claim.external_claim_id == external_claim_id).first()
    if existing is None:
        existing = Claim(tenant_id=tenant_id, member_id=member_id, external_claim_id=external_claim_id, **kwargs)
        db.add(existing)
        db.flush()
        print(f"  claim: {external_claim_id}")
    return existing


def seed_jubilee(db) -> None:
    """A second, independent tenant — proves the platform isn't secretly
    hardcoded to Minet. Same stub adapter, completely separate data: own
    tenant row, own users, own member, own provider panel, own appointments/
    prescriptions/labs/claims. Nothing here is shared with the Minet seed.
    """
    tenant = db.query(Tenant).filter(Tenant.slug == "jubilee").first()
    if tenant is None:
        tenant = Tenant(slug="jubilee", name="Jubilee Health Insurance", kind=TenantKind.INSURER, adapter_key="stub")
        db.add(tenant)
        db.flush()
        print(f"created tenant: {tenant.slug} ({tenant.id})")
    else:
        print(f"tenant already exists: {tenant.slug} ({tenant.id})")

    admin = db.query(User).filter(User.tenant_id == tenant.id, User.email == "admin@jubilee.test").first()
    if admin is None:
        admin = User(tenant_id=tenant.id, email="admin@jubilee.test", password_hash=hash_password("ChangeMe123!"), role=UserRole.TENANT_ADMIN, full_name="Jubilee Demo Admin")
        db.add(admin)
        print("created user: admin@jubilee.test / ChangeMe123!")
    else:
        print("user already exists: admin@jubilee.test")

    hospital_staff = db.query(User).filter(User.tenant_id == tenant.id, User.email == "hospital@jubilee.test").first()
    if hospital_staff is None:
        hospital_staff = User(tenant_id=tenant.id, email="hospital@jubilee.test", password_hash=hash_password("ChangeMe123!"), role=UserRole.PROVIDER_PARTICIPANT, full_name="Jubilee Demo Hospital Staff")
        db.add(hospital_staff)
        print("created user: hospital@jubilee.test / ChangeMe123! (provider_participant)")
    else:
        print("user already exists: hospital@jubilee.test")

    principal = db.query(Member).filter(Member.tenant_id == tenant.id, Member.external_ref == "JUB-2208-KL").first()
    if principal is None:
        principal = Member(
            tenant_id=tenant.id,
            external_ref="JUB-2208-KL",
            full_name="Grace Wanjiru",
            is_principal=True,
            scheme="Jubilee Elite Family Plan",
            plan="POL-JUB-551209",
            status=MemberStatus.ACTIVE,
            coverage_start=date(2026, 1, 1),
            coverage_end=date(2026, 12, 31),
            source="seed:scripts/seed.py",
            retrieved_at=datetime.now(timezone.utc),
        )
        db.add(principal)
        db.flush()
        print(f"created member: {principal.full_name} ({principal.id})")
    else:
        print(f"member already exists: {principal.full_name}")

    member_user = db.query(User).filter(User.tenant_id == tenant.id, User.email == "member@jubilee.test").first()
    if member_user is None:
        member_user = User(tenant_id=tenant.id, email="member@jubilee.test", password_hash=hash_password("ChangeMe123!"), role=UserRole.MEMBER, full_name=principal.full_name, member_id=principal.id)
        db.add(member_user)
        print("created user: member@jubilee.test / ChangeMe123! (member, linked to Grace Wanjiru)")
    else:
        print("user already exists: member@jubilee.test")

    print("jubilee dependants:")
    get_or_create_dependant(db, tenant.id, principal, "JUB-DEP-001", full_name="Kevin Wanjiru", relationship_to_principal="Son", date_of_birth=date(2015, 9, 12), status=MemberStatus.ACTIVE)
    get_or_create_dependant(db, tenant.id, principal, "JUB-DEP-002", full_name="Michael Wanjiru", relationship_to_principal="Spouse", date_of_birth=date(1988, 4, 2), status=MemberStatus.ACTIVE)

    print("jubilee providers:")
    dr_mugo = get_or_create_provider(db, tenant.id, "JUB-PRV-001", name="Dr. Felix Mugo", type=ProviderType.CLINICIAN, specialties=["General Physician"], location="Jubilee Medical Centre, Westlands", telemedicine_capable=True, integration_level=IntegrationLevel.PORTAL)
    dr_wafula = get_or_create_provider(db, tenant.id, "JUB-PRV-002", name="Dr. Esther Wafula", type=ProviderType.CLINICIAN, specialties=["Paediatrician"], location="MP Shah Hospital, Parklands", telemedicine_capable=False, integration_level=IntegrationLevel.DIRECT_API)
    get_or_create_provider(db, tenant.id, "JUB-PRV-003", name="Dr. Brian Kiptoo", type=ProviderType.CLINICIAN, specialties=["Orthopedic Surgeon"], location="Karen Hospital", telemedicine_capable=True, integration_level=IntegrationLevel.MINET_ASSISTED)

    mp_shah = get_or_create_provider(db, tenant.id, "JUB-FAC-001", name="MP Shah Hospital", type=ProviderType.FACILITY, specialties=["Hospital"], location="Parklands", integration_level=IntegrationLevel.DIRECT_API, latitude=-1.2672, longitude=36.8171, geofence_meters=350)
    mp_shah.latitude, mp_shah.longitude, mp_shah.geofence_meters = -1.2672, 36.8171, 350
    jub_lab = get_or_create_provider(db, tenant.id, "JUB-LAB-001", name="Metropolis Star Laboratories", type=ProviderType.LABORATORY, specialties=["Laboratory"], location="Multiple branches", integration_level=IntegrationLevel.PORTAL)
    jub_pharmacy = get_or_create_provider(db, tenant.id, "JUB-PH-001", name="Mediplus Pharmacy", type=ProviderType.PHARMACY, specialties=["Pharmacy"], location="Delivery & collection", integration_level=IntegrationLevel.PORTAL)

    hospital_staff.provider_id = dr_wafula.id  # physical, REQUESTED appointment below — approval demo
    clinician_mugo = db.query(User).filter(User.tenant_id == tenant.id, User.email == "clinician@jubilee.test").first()
    if clinician_mugo is None:
        clinician_mugo = User(tenant_id=tenant.id, email="clinician@jubilee.test", password_hash=hash_password("ChangeMe123!"), role=UserRole.CLINICIAN, full_name="Dr. Felix Mugo", provider_id=dr_mugo.id)
        db.add(clinician_mugo)
        print("created user: clinician@jubilee.test / ChangeMe123! (clinician, linked to Dr. Felix Mugo — telemedicine chat demo)")
    else:
        clinician_mugo.provider_id = dr_mugo.id
        print("user already exists: clinician@jubilee.test")

    print("jubilee appointments + consultations:")
    now = datetime.now(timezone.utc)
    jappt1 = get_or_create_appointment(db, tenant.id, principal.id, dr_mugo.id, "seed-jub-appt-1", mode=AppointmentMode.TELEMEDICINE, scheduled_at=now + timedelta(days=3), status=AppointmentStatus.CONFIRMED, cover_confirmed=True, cover_check_source="stub:eligibility-api", cover_check_at=now)
    jappt2 = get_or_create_appointment(db, tenant.id, principal.id, dr_wafula.id, "seed-jub-appt-2", mode=AppointmentMode.PHYSICAL, scheduled_at=now + timedelta(days=10), status=AppointmentStatus.REQUESTED, cover_confirmed=False, cover_check_source="stub:eligibility-api", cover_check_at=now)

    jc1 = get_or_create_consultation(db, tenant.id, jappt1.id, status=ConsultationStatus.COMPLETED, consent_captured_at=now, identity_verified=True, location_confirmed=True, clinician_identity_verified=True)
    get_or_create_consultation(db, tenant.id, jappt2.id, status=ConsultationStatus.PENDING_CONSENT)

    print("jubilee prescriptions:")
    jrx1 = get_or_create_recommendation(db, tenant.id, principal.id, jc1.id, RecommendationKind.PRESCRIPTION, {"ref": "JUB-RX-1001", "drug": "Ibuprofen 400mg", "dose": "1 tablet - as needed - 5 days", "by": "Dr. Felix Mugo"}, requires_preauth=False)
    get_or_create_order(db, tenant.id, principal.id, jrx1.id, jub_pharmacy.id, FulfilmentKind.PHARMACY, status=FulfilmentStatus.DISPENSED, fulfilled_at=now - timedelta(days=4))

    print("jubilee lab tests:")
    jlab1 = get_or_create_recommendation(db, tenant.id, principal.id, jc1.id, RecommendationKind.LAB_TEST, {"ref": "JUB-LAB-9001", "test": "Full Blood Count", "type": "Blood test"}, requires_preauth=False)
    get_or_create_order(db, tenant.id, principal.id, jlab1.id, jub_lab.id, FulfilmentKind.LABORATORY, status=FulfilmentStatus.RESULT_READY, result_ref="doc:jub-lab-9001-result.pdf", fulfilled_at=now - timedelta(days=4))

    print("jubilee claims:")
    get_or_create_claim(db, tenant.id, principal.id, "JUB-CLM-5001", appointment_id=jappt1.id, status=ClaimStatus.APPROVED, lines=[{"provider": "Jubilee Medical Centre", "service": "Teleconsultation", "amount": 2500, "covered": 2500, "member": 0}], submitted_at=now - timedelta(days=4))
    get_or_create_claim(db, tenant.id, principal.id, "JUB-CLM-5002", status=ClaimStatus.IN_REVIEW, lines=[{"provider": "Mediplus Pharmacy", "service": "Pharmacy", "amount": 1200, "covered": 1080, "member": 120}], submitted_at=now - timedelta(days=4))


def main() -> None:
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "minet").first()
        if tenant is None:
            tenant = Tenant(slug="minet", name="Minet", kind=TenantKind.MIP, adapter_key="stub")
            db.add(tenant)
            db.flush()
            print(f"created tenant: {tenant.slug} ({tenant.id})")
        else:
            print(f"tenant already exists: {tenant.slug} ({tenant.id})")

        admin = db.query(User).filter(User.tenant_id == tenant.id, User.email == "admin@minet.test").first()
        if admin is None:
            admin = User(
                tenant_id=tenant.id,
                email="admin@minet.test",
                password_hash=hash_password("ChangeMe123!"),
                role=UserRole.TENANT_ADMIN,
                full_name="Demo Admin",
            )
            db.add(admin)
            print("created user: admin@minet.test / ChangeMe123!")
        else:
            print("user already exists: admin@minet.test")

        hospital_staff = db.query(User).filter(User.tenant_id == tenant.id, User.email == "hospital@minet.test").first()
        if hospital_staff is None:
            hospital_staff = User(
                tenant_id=tenant.id,
                email="hospital@minet.test",
                password_hash=hash_password("ChangeMe123!"),
                role=UserRole.PROVIDER_PARTICIPANT,
                full_name="Demo Hospital Staff",
            )
            db.add(hospital_staff)
            print("created user: hospital@minet.test / ChangeMe123! (provider_participant)")
        else:
            print("user already exists: hospital@minet.test")

        # --- principal member (mirrors the stub adapter's MNT-0942-SC8591 record) ---
        principal = db.query(Member).filter(Member.tenant_id == tenant.id, Member.external_ref == MEMBER_REF).first()
        if principal is None:
            principal = Member(
                tenant_id=tenant.id,
                external_ref=MEMBER_REF,
                full_name="John Mwangi",
                is_principal=True,
                scheme="Minet Comprehensive Executive",
                plan="POL-MIN-884270",
                status=MemberStatus.ACTIVE,
                coverage_start=date(2026, 1, 1),
                coverage_end=date(2026, 12, 31),
                source="seed:scripts/seed.py",
                retrieved_at=datetime.now(timezone.utc),
            )
            db.add(principal)
            db.flush()
            print(f"created member: {principal.full_name} ({principal.id})")
        else:
            print(f"member already exists: {principal.full_name}")

        member_user = db.query(User).filter(User.tenant_id == tenant.id, User.email == "member@minet.test").first()
        if member_user is None:
            member_user = User(
                tenant_id=tenant.id,
                email="member@minet.test",
                password_hash=hash_password("ChangeMe123!"),
                role=UserRole.MEMBER,
                full_name=principal.full_name,
                member_id=principal.id,
            )
            db.add(member_user)
            print("created user: member@minet.test / ChangeMe123! (member, linked to John Mwangi)")
        else:
            print("user already exists: member@minet.test")

        print("dependants:")
        get_or_create_dependant(db, tenant.id, principal, "DEP-001234", full_name="Brian Mwangi", relationship_to_principal="Son", date_of_birth=date(2017, 3, 1), status=MemberStatus.ACTIVE)
        get_or_create_dependant(db, tenant.id, principal, "DEP-001235", full_name="Amina Mwangi", relationship_to_principal="Daughter", date_of_birth=date(2011, 6, 1), status=MemberStatus.ACTIVE)
        get_or_create_dependant(db, tenant.id, principal, "DEP-001236", full_name="Grace Mwangi", relationship_to_principal="Spouse", date_of_birth=date(1991, 1, 1), status=MemberStatus.ACTIVE)

        print("providers:")
        dr_amina = get_or_create_provider(db, tenant.id, "PRV-0001", name="Dr. Amina Njoroge", type=ProviderType.CLINICIAN, specialties=["General Physician"], location="Nairobi Health Labs", telemedicine_capable=True, integration_level=IntegrationLevel.MINET_ASSISTED)
        dr_peter = get_or_create_provider(db, tenant.id, "PRV-0002", name="Dr. Peter Otieno", type=ProviderType.CLINICIAN, specialties=["Cardiologist"], location="Aga Khan Hospital, Parklands", telemedicine_capable=False, integration_level=IntegrationLevel.PORTAL)
        dr_lydia = get_or_create_provider(db, tenant.id, "PRV-0003", name="Dr. Lydia Kamau", type=ProviderType.CLINICIAN, specialties=["Dermatologist"], location="Teleconsultation", telemedicine_capable=True, integration_level=IntegrationLevel.MINET_ASSISTED)
        get_or_create_provider(db, tenant.id, "PRV-0004", name="Dr. Samuel Kiprop", type=ProviderType.CLINICIAN, specialties=["Paediatrician"], location="Westlands, Nairobi", telemedicine_capable=True, integration_level=IntegrationLevel.PORTAL)
        get_or_create_provider(db, tenant.id, "PRV-0005", name="Dr. Halima Yusuf", type=ProviderType.CLINICIAN, specialties=["Gynaecologist"], location="Karen, Nairobi", telemedicine_capable=False, network_status="out_of_panel", integration_level=IntegrationLevel.MINET_ASSISTED)

        aga_khan = get_or_create_provider(db, tenant.id, "FAC-0001", name="Aga Khan University Hospital", type=ProviderType.FACILITY, specialties=["Hospital"], location="Parklands", integration_level=IntegrationLevel.PORTAL, latitude=-1.2626, longitude=36.8172, geofence_meters=400)
        nairobi_hospital = get_or_create_provider(db, tenant.id, "FAC-0002", name="Nairobi Hospital", type=ProviderType.FACILITY, specialties=["Hospital"], location="Upper Hill", integration_level=IntegrationLevel.PORTAL, latitude=-1.2960, longitude=36.8110, geofence_meters=400)
        # get_or_create_provider only sets these on first creation — backfill for reseeds of an already-seeded DB.
        aga_khan.latitude, aga_khan.longitude, aga_khan.geofence_meters = -1.2626, 36.8172, 400
        nairobi_hospital.latitude, nairobi_hospital.longitude, nairobi_hospital.geofence_meters = -1.2960, 36.8110, 400
        lancet = get_or_create_provider(db, tenant.id, "LAB-0001", name="Lancet Kenya Laboratories", type=ProviderType.LABORATORY, specialties=["Laboratory"], location="Multiple branches", integration_level=IntegrationLevel.DIRECT_API)
        pathcare = get_or_create_provider(db, tenant.id, "LAB-0002", name="Pathcare", type=ProviderType.LABORATORY, specialties=["Laboratory"], location="Multiple branches", integration_level=IntegrationLevel.PORTAL)
        goodlife = get_or_create_provider(db, tenant.id, "PH-0001", name="Goodlife Pharmacy", type=ProviderType.PHARMACY, specialties=["Pharmacy"], location="Delivery & collection", integration_level=IntegrationLevel.DIRECT_API)
        haltons = get_or_create_provider(db, tenant.id, "PH-0002", name="Haltons Pharmacy", type=ProviderType.PHARMACY, specialties=["Pharmacy"], location="Delivery & collection", integration_level=IntegrationLevel.PORTAL)

        # Link logins to the specific provider rows they act as/for — lets the
        # provider-portal appointment queue and chat scope correctly instead
        # of a facility login seeing the whole tenant.
        hospital_staff.provider_id = dr_peter.id  # physical, REQUESTED appointment below — approval demo
        clinician_amina = db.query(User).filter(User.tenant_id == tenant.id, User.email == "clinician@minet.test").first()
        if clinician_amina is None:
            clinician_amina = User(tenant_id=tenant.id, email="clinician@minet.test", password_hash=hash_password("ChangeMe123!"), role=UserRole.CLINICIAN, full_name="Dr. Amina Njoroge", provider_id=dr_amina.id)
            db.add(clinician_amina)
            print("created user: clinician@minet.test / ChangeMe123! (clinician, linked to Dr. Amina Njoroge — telemedicine chat demo)")
        else:
            clinician_amina.provider_id = dr_amina.id
            print("user already exists: clinician@minet.test")

        clinician_lydia = db.query(User).filter(User.tenant_id == tenant.id, User.email == "lydia@minet.test").first()
        if clinician_lydia is None:
            clinician_lydia = User(tenant_id=tenant.id, email="lydia@minet.test", password_hash=hash_password("ChangeMe123!"), role=UserRole.CLINICIAN, full_name="Dr. Lydia Kamau", provider_id=dr_lydia.id)
            db.add(clinician_lydia)
            print("created user: lydia@minet.test / ChangeMe123! (clinician, linked to Dr. Lydia Kamau)")
        else:
            clinician_lydia.provider_id = dr_lydia.id
            print("user already exists: lydia@minet.test")

        print("appointments + consultations:")
        now = datetime.now(timezone.utc)
        appt1 = get_or_create_appointment(db, tenant.id, principal.id, dr_amina.id, "seed-appt-1", mode=AppointmentMode.TELEMEDICINE, scheduled_at=now + timedelta(days=2), status=AppointmentStatus.CONFIRMED, cover_confirmed=True, cover_check_source="stub:eligibility-api", cover_check_at=now)
        appt2 = get_or_create_appointment(db, tenant.id, principal.id, dr_peter.id, "seed-appt-2", mode=AppointmentMode.PHYSICAL, scheduled_at=now + timedelta(days=8), status=AppointmentStatus.REQUESTED, cover_confirmed=False, cover_check_source="stub:eligibility-api", cover_check_at=now)
        appt3 = get_or_create_appointment(db, tenant.id, principal.id, dr_lydia.id, "seed-appt-3", mode=AppointmentMode.TELEMEDICINE, scheduled_at=now + timedelta(days=14), status=AppointmentStatus.REQUESTED, cover_confirmed=False, cover_check_source="stub:eligibility-api", cover_check_at=now)

        c1 = get_or_create_consultation(db, tenant.id, appt1.id, status=ConsultationStatus.COMPLETED, consent_captured_at=now, identity_verified=True, location_confirmed=True, clinician_identity_verified=True)
        c2 = get_or_create_consultation(db, tenant.id, appt2.id, status=ConsultationStatus.PENDING_CONSENT)
        c3 = get_or_create_consultation(db, tenant.id, appt3.id, status=ConsultationStatus.PENDING_CONSENT)

        print("prescriptions:")
        rx1 = get_or_create_recommendation(db, tenant.id, principal.id, c1.id, RecommendationKind.PRESCRIPTION, {"ref": "RX-20841", "drug": "Amoxicillin 500mg", "dose": "1 capsule - 3x daily - 7 days", "by": "Dr. Amina Njoroge"}, requires_preauth=False)
        get_or_create_order(db, tenant.id, principal.id, rx1.id, goodlife.id, FulfilmentKind.PHARMACY, status=FulfilmentStatus.DISPENSED, fulfilled_at=now - timedelta(days=7))

        rx2 = get_or_create_recommendation(db, tenant.id, principal.id, c2.id, RecommendationKind.PRESCRIPTION, {"ref": "RX-20790", "drug": "Metformin 850mg", "dose": "1 tablet - 2x daily - 30 days", "by": "Dr. Peter Otieno"}, requires_preauth=True)
        get_or_create_order(db, tenant.id, principal.id, rx2.id, goodlife.id, FulfilmentKind.PHARMACY, status=FulfilmentStatus.PLACED)

        rx3 = get_or_create_recommendation(db, tenant.id, principal.id, c1.id, RecommendationKind.PRESCRIPTION, {"ref": "RX-20512", "drug": "Cetirizine 10mg", "dose": "1 tablet - nightly - 14 days", "by": "Dr. Lydia Kamau"}, requires_preauth=False)
        get_or_create_order(db, tenant.id, principal.id, rx3.id, haltons.id, FulfilmentKind.PHARMACY, status=FulfilmentStatus.DISPENSED, fulfilled_at=now - timedelta(days=20))

        rx4 = get_or_create_recommendation(db, tenant.id, principal.id, c2.id, RecommendationKind.PRESCRIPTION, {"ref": "RX-20377", "drug": "Atorvastatin 20mg", "dose": "1 tablet - nightly - 30 days", "by": "Dr. Peter Otieno"}, requires_preauth=False)
        get_or_create_order(db, tenant.id, principal.id, rx4.id, goodlife.id, FulfilmentKind.PHARMACY, status=FulfilmentStatus.DISPENSED, fulfilled_at=now - timedelta(days=35))

        print("lab tests:")
        lab1 = get_or_create_recommendation(db, tenant.id, principal.id, c1.id, RecommendationKind.LAB_TEST, {"ref": "LAB-5521", "test": "Complete Blood Count", "type": "Blood test"}, requires_preauth=False)
        get_or_create_order(db, tenant.id, principal.id, lab1.id, lancet.id, FulfilmentKind.LABORATORY, status=FulfilmentStatus.RESULT_READY, result_ref="doc:lab-5521-result.pdf", fulfilled_at=now - timedelta(days=9))

        lab2 = get_or_create_recommendation(db, tenant.id, principal.id, c2.id, RecommendationKind.LAB_TEST, {"ref": "LAB-5530", "test": "Lipid Profile", "type": "Blood test"}, requires_preauth=True)
        get_or_create_order(db, tenant.id, principal.id, lab2.id, pathcare.id, FulfilmentKind.LABORATORY, status=FulfilmentStatus.IN_PROGRESS)

        lab3 = get_or_create_recommendation(db, tenant.id, principal.id, c3.id, RecommendationKind.LAB_TEST, {"ref": "LAB-5544", "test": "MRI Lumbar Spine", "type": "Imaging"}, requires_preauth=True)
        get_or_create_order(db, tenant.id, principal.id, lab3.id, aga_khan.id, FulfilmentKind.LABORATORY, status=FulfilmentStatus.PLACED)

        lab4 = get_or_create_recommendation(db, tenant.id, principal.id, c1.id, RecommendationKind.LAB_TEST, {"ref": "LAB-5470", "test": "HbA1c", "type": "Blood test"}, requires_preauth=False)
        get_or_create_order(db, tenant.id, principal.id, lab4.id, lancet.id, FulfilmentKind.LABORATORY, status=FulfilmentStatus.RESULT_READY, result_ref="doc:lab-5470-result.pdf", fulfilled_at=now - timedelta(days=27))

        print("claims:")
        get_or_create_claim(db, tenant.id, principal.id, "CLM-78493", appointment_id=appt1.id, status=ClaimStatus.APPROVED, lines=[{"provider": "Aga Khan Hospital", "service": "Consultation & labs", "amount": 14500, "covered": 14500, "member": 0}], submitted_at=now - timedelta(days=9))
        get_or_create_claim(db, tenant.id, principal.id, "CLM-78211", status=ClaimStatus.IN_REVIEW, lines=[{"provider": "Goodlife Pharmacy", "service": "Pharmacy", "amount": 3200, "covered": 2880, "member": 320}], submitted_at=now - timedelta(days=15))
        get_or_create_claim(db, tenant.id, principal.id, "CLM-77980", status=ClaimStatus.PAID, lines=[{"provider": "Lancet Kenya", "service": "Diagnostics", "amount": 9800, "covered": 9800, "member": 0}], submitted_at=now - timedelta(days=20))
        get_or_create_claim(db, tenant.id, principal.id, "CLM-77412", status=ClaimStatus.NEEDS_ACTION, lines=[{"provider": "Nairobi Hospital", "service": "Specialist consultation", "amount": 8500, "covered": 0, "member": 8500}], submitted_at=now - timedelta(days=31))

        print()
        print("--- jubilee tenant ---")
        seed_jubilee(db)

        db.commit()
        print("done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
