# src/bot/telegram_worker.py
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models import Notification
from src.bot.telegram_sender import TelegramNotificationSender
from src.utils.logger_config import app_logger as logger
from src.notification.notification_dispatcher import dispatch_pending_notifications

async def notification_worker(sender: TelegramNotificationSender, poll_interval: float = 30.0):
    """
    Worker que revisa notificaciones 'pending' y 'ready'.
    1️⃣ Pasa 'pending' a 'ready' usando el dispatcher
    2️⃣ Envía las notificaciones 'ready' al usuario
    """
    while True:
        db: Session = SessionLocal()
        try:
            # =========================
            # 1️⃣ Pasar pending -> ready
            # =========================
            try:
                processed = dispatch_pending_notifications(db, now=datetime.utcnow())
                if processed:
                    logger.info(f"Dispatcher: {processed} notificaciones marcadas como 'ready'")
            except Exception as e:
                logger.exception(f"Error en dispatcher: {e}")

            # =========================
            # 2️⃣ Enviar notificaciones 'ready'
            # =========================
            ready_notifications = db.query(Notification).filter(Notification.status == "ready").all()

            for notification in ready_notifications:
                try:
                    await sender.send(notification, db)
                    logger.info(f"Notificación ID={notification.id} enviada a Telegram")
                except Exception as e:
                    logger.exception(f"Error enviando notificación ID={notification.id}: {e}")
                    notification.attempts += 1
                    notification.status = "failed"
                    db.commit()

        finally:
            db.close()

        await asyncio.sleep(poll_interval)
