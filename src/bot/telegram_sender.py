# src/notifications/telegram_sender.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application
from src.models import Notification
from datetime import datetime

from src.services.telegram_identity_service import get_identity_by_user_id

from sqlalchemy.orm import Session


class TelegramNotificationSender:
    def __init__(self, app: Application):
        self.app = app

    async def send(self, notification: Notification, db: Session):
        user = notification.user
        if not user:
            raise ValueError("El usuario no existe para esta notificación")

        identity = get_identity_by_user_id(db, user.id)
        if not identity:
            raise ValueError("El usuario no tiene identidad de Telegram activa")

        telegram_id = identity.telegram_user_id
        if not telegram_id:
            raise ValueError("El usuario no tiene Telegram vinculado")

        match_id = notification.payload.get("match_id")
        if not match_id:
            raise ValueError("Payload no tiene match_id")

        keyboard = [
            [
                InlineKeyboardButton("Gané ✅", callback_data=f"match_result:{match_id}:win"),
                InlineKeyboardButton("Perdí ❌", callback_data=f"match_result:{match_id}:lose"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "El partido terminó. ¿Ganaste o perdiste?"

        # ⚡ Enviar mensaje con await
        await self.app.bot.send_message(
            chat_id=telegram_id,
            text=text,
            reply_markup=reply_markup
        )

        # ⚡ Guardar cambios en DB con try/finally
        try:
            notification.status = "sent"
            notification.sent_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"No se pudo marcar la notificación como enviada: {e}")
