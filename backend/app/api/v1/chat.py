import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_db_user, get_current_user, get_ws_current_user
from app.models.chat import ChatSenderRole
from app.models.notification import NotificationType
from app.models.user import User
from app.schemas.chat import ChatMessageOut
from app.services import chat as chat_service
from app.services import notifications as notification_service
from app.services.chat_hub import hub

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/{consultation_id}/messages", response_model=list[ChatMessageOut])
def get_messages(
    consultation_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> list[ChatMessageOut]:
    chat_service.authorize_consultation_access(
        db, tenant_id=current.tenant_id, user=user, role=current.role, consultation_id=consultation_id
    )
    return chat_service.list_messages(db, consultation_id)


@router.websocket("/{consultation_id}/ws")
async def chat_ws(websocket: WebSocket, consultation_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
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

    sender_role = chat_service.sender_role_for(current.role)
    await hub.connect(consultation_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                body = (data.get("body") or "").strip()
                if not body:
                    continue
                message = chat_service.create_message(
                    db, tenant_id=current.tenant_id, consultation_id=consultation_id,
                    sender_user_id=current.user_id, sender_role=sender_role, body=body,
                )
                recipient_ids = chat_service.resolve_counterpart_user_ids(
                    db, tenant_id=current.tenant_id, appointment=appointment, sender_role=sender_role
                )
                link = f"/provider/chat/{appointment.id}" if sender_role == ChatSenderRole.MEMBER else f"/portal/chat/{appointment.id}"
                preview = body if len(body) <= 80 else f"{body[:77]}..."
                for recipient_id in recipient_ids:
                    await notification_service.notify(
                        db, tenant_id=current.tenant_id, user_id=recipient_id,
                        type=NotificationType.CHAT_MESSAGE,
                        title=f"New message from {user.full_name}",
                        body=preview, link=link,
                    )
                db.commit()
                await hub.broadcast(consultation_id, {
                    "type": "message",
                    "id": str(message.id),
                    "sender_role": sender_role.value,
                    "body": message.body,
                    "created_at": message.created_at.isoformat(),
                })

            elif msg_type == "typing":
                await hub.broadcast(consultation_id, {"type": "typing", "sender_role": sender_role.value})

            elif msg_type == "read":
                newly_read = chat_service.mark_read(db, consultation_id=consultation_id, reader_role=sender_role)
                db.commit()
                if newly_read:
                    await hub.broadcast(consultation_id, {"type": "read", "reader_role": sender_role.value})
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(consultation_id, websocket)
