# src/notification/notification_dispatcher.py
from datetime import datetime
from sqlalchemy.orm import Session
from src.models import Notification
from src.notification.notification_rules import can_send_notification
from src.utils.logger_config import app_logger as logger
from src.services.match_service import process_pending_match_result_replies, get_open_matches, try_close_match_if_ready


def dispatch_pending_notifications(
    db: Session,
    now: datetime | None = None,
    limit: int = 50
) -> int:
    now = now or datetime.utcnow()
    logger.info(f"Dispatch iniciado a las {now.isoformat()}")

    # ==========================
    # 1. Procesar resultados pendientes de matches
    # ==========================
    try:
        process_pending_match_result_replies(db)
    except Exception:
        logger.exception("Error procesando MatchResultReply")
        db.rollback()

    # ==========================
    # 2. Intentar cerrar partidos
    # ==========================
    try:
        open_matches = get_open_matches(db)
        for match in open_matches:
            try_close_match_if_ready(match, db)
    except Exception:
        logger.exception("Error cerrando matches")
        db.rollback()

    # ==========================
    # 3. Despachar notificaciones
    # ==========================
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
        notification.status = "ready"
        processed += 1

    db.commit()

    logger.info(f"Dispatch finalizado. Notificaciones procesadas: {processed}")
    return processed
