# src/bot/handlers/telegram_callbacks.py
from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler, ContextTypes
from sqlalchemy.orm import Session

from src.database import get_db  # función que devuelve sesión SQLAlchemy
from src.bot.bot_handlers.telegram_match_evaluation import handle_telegram_reply  # tu función

# --------------------------
# Función que maneja los clicks de los botones
# --------------------------
async def process_match_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db = next(get_db())  # <-- aquí obtenés la sesión síncrona
    try:
        telegram_user_id = query.from_user.id
        callback_data = query.data
        result = handle_telegram_reply(db, telegram_user_id, callback_data)
    finally:
        db.close()

    await query.edit_message_text(result["text"])
