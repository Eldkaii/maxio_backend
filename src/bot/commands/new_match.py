from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from src.api_clients.users_api import UsersAPIClient

users_api = UsersAPIClient()


async def cancel_new_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_match", None)

    await update.message.reply_text(
        "❌ Creación de partido cancelada."
    )

    return ConversationHandler.END