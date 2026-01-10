# src/bot/commands/logout.py
from telegram import Update
from telegram.ext import ContextTypes
from src.database import get_db
from src.services.telegram_identity_service import get_identity_by_telegram_user_id, unlink_identity_from_user

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = next(get_db())
    tg_user_id = update.effective_user.id
    identity = get_identity_by_telegram_user_id(db, tg_user_id)

    if identity:
        unlink_identity_from_user(db, identity)

    context.user_data.clear()

    await update.message.reply_text(
        "✅ Te deslogueaste correctamente.\n"
        "Cuando quieras, podés usar /start para iniciar sesión nuevamente."
    )
