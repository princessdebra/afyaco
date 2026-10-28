import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.services.reminders import run_reminder_loop

logger = logging.getLogger("afyaco")

app = FastAPI(
    title="Afyaco (Xenova Connected Medical Operations) API",
    description="Care navigation, booking, pre-authorisation and claims orchestration. "
    "Insurer/MIP integrations are pluggable via app.adapters — only a mock 'stub' "
    "adapter is wired up today; real tenant integrations are deferred.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5180"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
def warm_up_biometric_provider() -> None:
    """Loads the configured biometric provider's models at boot (model/weight
    loading can take real time for the open-source CV provider) so a boot
    failure surfaces in deploy logs instead of on some member's first request.
    """
    from app.biometrics.registry import get_provider

    try:
        provider = get_provider()
        logger.info("Biometric provider '%s' loaded.", provider.key)
    except Exception:
        logger.exception("Failed to load biometric provider at startup.")
        raise


@app.on_event("startup")
async def start_reminder_loop() -> None:
    app.state.reminder_task = asyncio.create_task(run_reminder_loop())


@app.on_event("shutdown")
async def stop_reminder_loop() -> None:
    task = getattr(app.state, "reminder_task", None)
    if task is not None:
        task.cancel()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
