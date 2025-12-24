from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.services.telegram_identity_service import (
    create_identity_if_not_exists,
    is_identity_linked,
)
from src.database import get_db


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if tg_user is None:
        return

    db = next(get_db())

    identity = create_identity_if_not_exists(
        db=db,
        telegram_user_id=tg_user.id,
        telegram_username=tg_user.username
    )

    if is_identity_linked(identity):
        await update.message.reply_text(
            "👋 Bienvenido a Max_io.\n"
            f"Tu usuario {identity} ya está vinculada."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton("🆕 Soy nuevo jugador", callback_data="auth:new"),
            InlineKeyboardButton("🔑 Ya tengo cuenta", callback_data="auth:existing"),
        ]
    ]

    await update.message.reply_text(
        "👋 Bienvenido a Max_io.\n"
        "No encontramos una cuenta asociada.\n\n"
        "¿Qué querés hacer?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
