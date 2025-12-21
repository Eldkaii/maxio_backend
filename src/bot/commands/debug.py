# src/bot/commands/debug.py

from telegram import Update
from telegram.ext import ContextTypes

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🧪 DEBUG\n"
        f"telegram_user_id: {user.id}\n"
        f"username: {user.username}\n"
        f"name: {user.first_name}"
    )
