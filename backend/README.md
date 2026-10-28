# Afyaco backend (Xenova Connected Medical Operations)

Python/FastAPI backend implementing the platform-side workflow from the
developer brief: booking, consultations, pre-authorisation and claims
**orchestration** — built so a new insurer/MIP/TPA can be plugged in later
without touching this code.

## What's here vs. what's deferred

This backend deliberately does **not** implement any real external insurer
integration yet (no live Minet API client, no FAWE, no telemedia provider, no
pharmacy/lab partner calls). Instead it builds the full platform around a
clean **adapter boundary** (`app/adapters/base.py`) so that work is a matter of
writing one class per tenant later, not restructuring the platform:

- `app/adapters/base.py` — the interface every tenant integration must
  implement: member lookup, eligibility, benefits, provider panel search,
  pre-auth, claims, notifications.
- `app/adapters/stub.py` — a deterministic mock implementation (`StubAdapter`)
  used for every tenant today, so the rest of the system can be built and
  tested end-to-end. Every value it returns is tagged `source: "stub:..."`.
- `app/adapters/registry.py` — maps a `Tenant.adapter_key` to a concrete
  adapter instance. Onboarding insurer "Acme" later means: write
  `app/adapters/acme.py` implementing `TenantAdapter`, register it here, set
  `adapter_key="acme"` on that tenant row. Nothing else changes.

Everything else — tenancy/auth, the canonical data model, booking workflow,
pre-auth/claims orchestration state machines, and audit logging — is real,
working backend logic, independent of which adapter is plugged in.

## Architecture

```
app/
  core/        settings, DB session, JWT auth, tenancy dependencies
  models/      SQLAlchemy ORM — the platform's own operational data
  schemas/
    canonical.py   the canonical Xenova model (brief §4) — the shape every
                    adapter must return, regardless of the tenant's own API
    auth.py, member.py, appointment.py, preauth.py, claim.py
                    request/response schemas for the HTTP API
  adapters/    the integration boundary (see above)
  services/    business logic: booking, pre-auth, claims, member sync, audit
  api/v1/      FastAPI routers
alembic/       migrations
scripts/seed.py   bootstraps a demo tenant/user/provider
```

### Multi-tenancy

Every operational table carries `tenant_id`. `app/core/deps.py` resolves the
caller's tenant from their JWT and `get_tenant_adapter()` resolves which
adapter (currently always `stub`) backs that tenant's integration calls. A
real "onboard a new insurer" flow is: insert a `Tenant` row with its own
`adapter_key`, write/register that adapter — the booking, pre-auth and claims
services never need to know which tenant they're running for.

### Canonical model

Routers and services never see a tenant's native API shape. Adapters return
`app/schemas/canonical.py` types (`MemberRecord`, `EligibilityResult`,
`BenefitRecord`, `ProviderRecord`, `PreAuthResult`, `ClaimResult`) and
everything downstream works against those only (brief §4).

### What's implemented end-to-end

- JWT auth, tenant-scoped (`POST /api/v1/auth/login`)
- Member resolution + local operational cache with staleness check
  (`GET /api/v1/members/{external_ref}`) and live benefit lookup
  (`GET /api/v1/members/{external_ref}/benefits`)
- Appointment booking with an eligibility check snapshot and idempotency key
  (`POST/GET /api/v1/appointments`)
- Pre-authorisation orchestration: requirement check → submission → status
  (`POST/GET /api/v1/preauth`)
- Claim submission and status (`POST/GET /api/v1/claims`)
- Append-only audit log written by every service above

### Modelled but not yet wired to a router

`Consultation`, `ClinicalRecommendation` and `FulfilmentOrder` (pharmacy/lab)
tables exist (`app/models/`) to carry the brief's full journey, but their API
routes aren't built yet — add `app/api/v1/consultations.py` and
`app/api/v1/fulfilment.py` following the same pattern as `appointments.py`
when you're ready for that slice.

### Deliberately not started

FAWE integration, a real telemedicine/video provider, and any concrete
insurer HTTP client — these all require an external party's actual API
contract, which is why they're out of scope for now per your instruction.

## Running locally

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # adjust DATABASE_URL if needed

docker compose up -d            # starts local Postgres
alembic revision --autogenerate -m "init"
alembic upgrade head
python scripts/seed.py          # creates tenant 'minet' + admin@minet.test / ChangeMe123!

uvicorn app.main:app --reload --port 8000
# docs at http://localhost:8000/docs
```

Login with `tenant_slug: minet`, `email: admin@minet.test`,
`password: ChangeMe123!` to get a bearer token for the other endpoints.
