# src/notification/notification_dispatcher.py
from datetime import datetime
from sqlalchemy.orm import Session
from src.models import Notification
from src.notification.notification_rules import can_send_notification
from src.utils.logger_config import app_logger as logger

def dispatch_pending_notifications(db: Session, now: datetime | None = None, limit: int = 50) -> int:
    now = now or datetime.utcnow()
    logger.info(f"Dispatch iniciado a las {now.isoformat()}")

    notifications = (
        db.query(Notification)
        .filter(
            Notification.status == "pending",
            Notification.available_at <= now,
        )
        .order_by(Notification.available_at)
        .limit(limit)
        .all()
    )

    processed = 0

    for notification in notifications:
        if not can_send_notification(db, notification, now):
            continue
        # ⚡ Solo marcarla como ready para enviar
        notification.status = "ready"
        db.commit()
        processed += 1

    logger.info(f"Dispatch finalizado. Total procesadas: {processed}")
    return processed
