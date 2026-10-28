import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.db import SessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.notification import NotificationType
from app.models.user import User
from app.services import notifications as notification_service

logger = logging.getLogger("afyaco.reminders")

REMINDER_WINDOW = timedelta(minutes=15)
POLL_INTERVAL_SECONDS = 60


async def _send_due_reminders() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = (
            db.query(Appointment)
            .filter(
                Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.RESCHEDULED]),
                Appointment.reminder_sent.is_(False),
                Appointment.scheduled_at > now,
                Appointment.scheduled_at <= now + REMINDER_WINDOW,
            )
            .all()
        )
        for appointment in due:
            when = appointment.scheduled_at.strftime("%-I:%M %p")
            mode_label = "video call" if appointment.mode.value == "telemedicine" else "in-person visit"

            member_users = db.query(User).filter(
                User.tenant_id == appointment.tenant_id, User.member_id == appointment.member_id
            ).all()
            for u in member_users:
                await notification_service.notify(
                    db, tenant_id=appointment.tenant_id, user_id=u.id,
                    type=NotificationType.APPOINTMENT_REMINDER,
                    title="Appointment in 15 minutes",
                    body=f"Your {mode_label} is at {when}.",
                    link=f"/portal/appointments/{appointment.id}",
                )

            provider_users = db.query(User).filter(
                User.tenant_id == appointment.tenant_id, User.provider_id == appointment.provider_id
            ).all()
            for u in provider_users:
                await notification_service.notify(
                    db, tenant_id=appointment.tenant_id, user_id=u.id,
                    type=NotificationType.APPOINTMENT_REMINDER,
                    title="Appointment in 15 minutes",
                    body=f"Your {mode_label} is at {when}.",
                    link=f"/provider/appointments",
                )

            appointment.reminder_sent = True

        if due:
            db.commit()
            logger.info("Sent reminders for %d appointment(s).", len(due))
    except Exception:
        db.rollback()
        logger.exception("Reminder sweep failed.")
    finally:
        db.close()


async def run_reminder_loop() -> None:
    """Started once at app startup (see app/main.py). Polls rather than
    scheduling exact-time jobs — simple, and fine at this data volume; a
    heavier deployment would use a real scheduler (Celery beat, APScheduler)
    instead of an in-process loop.
    """
    while True:
        try:
            await _send_due_reminders()
        except Exception:
            logger.exception("Unexpected error in reminder loop.")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
