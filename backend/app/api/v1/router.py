from fastapi import APIRouter

from app.api.v1 import (
    appointments,
    auth,
    call,
    chat,
    claims,
    consultations,
    identity,
    members,
    notifications,
    preauth,
    providers,
    recommendations,
    translation,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(members.router)
api_router.include_router(providers.router)
api_router.include_router(appointments.router)
api_router.include_router(consultations.router)
api_router.include_router(preauth.router)
api_router.include_router(claims.router)
api_router.include_router(recommendations.router)
api_router.include_router(identity.router)
api_router.include_router(translation.router)
api_router.include_router(chat.router)
api_router.include_router(call.router)
api_router.include_router(notifications.router)
