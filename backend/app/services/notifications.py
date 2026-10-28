import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.services.notification_hub import hub


async def notify(
    db: Session, *, tenant_id: uuid.UUID, user_id: uuid.UUID, type: NotificationType,
    title: str, body: str, link: str | None = None,
) -> Notification:
    """Creates the durable record AND pushes it live if that user has a
    notifications WebSocket open. Always call this instead of writing a
    Notification row directly — the push is the whole point.
    """
    n = Notification(tenant_id=tenant_id, user_id=user_id, type=type, title=title, body=body, link=link)
    db.add(n)
    db.flush()
    await hub.push(user_id, {
        "type": "notification",
        "id": str(n.id),
        "notification_type": n.type.value,
        "title": n.title,
        "body": n.body,
        "link": n.link,
        "created_at": n.created_at.isoformat(),
    })
    return n


def list_notifications(db: Session, *, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def unread_count(db: Session, *, user_id: uuid.UUID) -> int:
    return db.query(Notification).filter(Notification.user_id == user_id, Notification.read_at.is_(None)).count()


def mark_read(db: Session, *, user_id: uuid.UUID, notification_id: uuid.UUID | None = None) -> int:
    """Marks one notification (or, if notification_id is None, everything
    unread) as read for this user. Returns how many were updated."""
    query = db.query(Notification).filter(Notification.user_id == user_id, Notification.read_at.is_(None))
    if notification_id is not None:
        query = query.filter(Notification.id == notification_id)
    rows = query.all()
    now = datetime.now(timezone.utc)
    for row in rows:
        row.read_at = now
    db.flush()
    return len(rows)
