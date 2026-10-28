import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_ws_current_user
from app.models.chat import ChatSenderRole
from app.models.notification import NotificationType
from app.models.user import User
from app.services import chat as chat_service
from app.services import notifications as notification_service
from app.services.signal_hub import hub

router = APIRouter(prefix="/call", tags=["call"])


@router.websocket("/{consultation_id}/signal")
async def call_signal_ws(websocket: WebSocket, consultation_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Pure signaling relay — SDP offers/answers and ICE candidates pass
    through here so the two browsers can set up a direct peer-to-peer
    WebRTC connection. No media ever touches this server.
    """
    current = get_ws_current_user(websocket, db)
    user = db.query(User).filter(User.id == current.user_id, User.tenant_id == current.tenant_id).first()
    if user is None:
        await websocket.close(code=1008)
        return

    try:
        _, appointment = chat_service.authorize_consultation_access(
            db, tenant_id=current.tenant_id, user=user, role=current.role, consultation_id=consultation_id
        )
    except Exception:
        await websocket.close(code=1008)
        return

    # First to join is "calling" the other side — push a real incoming-call
    # notification (bell + toast), not just a page that works if they
    # happen to already be looking at it.
    is_first_to_join = not hub.rooms.get(consultation_id)
    if is_first_to_join:
        sender_role = chat_service.sender_role_for(current.role)
        recipient_ids = chat_service.resolve_counterpart_user_ids(
            db, tenant_id=current.tenant_id, appointment=appointment, sender_role=sender_role
        )
        link = f"/provider/call/{appointment.id}" if sender_role == ChatSenderRole.MEMBER else f"/portal/call/{appointment.id}"
        for recipient_id in recipient_ids:
            await notification_service.notify(
                db, tenant_id=current.tenant_id, user_id=recipient_id,
                type=NotificationType.INCOMING_CALL,
                title=f"{user.full_name} is calling",
                body="Video consultation — tap to join",
                link=link,
            )
        db.commit()

    await hub.connect(consultation_id, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            await hub.relay(consultation_id, websocket, payload)
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(consultation_id, websocket)
        await hub.relay(consultation_id, websocket, {"type": "peer-left"})
