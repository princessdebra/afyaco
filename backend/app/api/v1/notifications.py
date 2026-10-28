import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, get_ws_current_user
from app.models.notification import Notification
from app.schemas.notification import NotificationOut, UnreadCountOut
from app.services import notifications as notification_service
from app.services.notification_hub import hub

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_my_notifications(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notification]:
    return notification_service.list_notifications(db, user_id=current.user_id)


@router.get("/unread-count", response_model=UnreadCountOut)
def my_unread_count(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnreadCountOut:
    return UnreadCountOut(count=notification_service.unread_count(db, user_id=current.user_id))


@router.post("/read-all")
def mark_all_read(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    n = notification_service.mark_read(db, user_id=current.user_id)
    db.commit()
    return {"marked_read": n}


@router.post("/{notification_id}/read")
def mark_one_read(
    notification_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    n = notification_service.mark_read(db, user_id=current.user_id, notification_id=notification_id)
    db.commit()
    return {"marked_read": n}


@router.websocket("/ws")
async def notifications_ws(websocket: WebSocket, db: Session = Depends(get_db)) -> None:
    current = get_ws_current_user(websocket, db)
    await hub.connect(current.user_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # client doesn't send anything meaningful; just keep the socket open
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(current.user_id, websocket)
