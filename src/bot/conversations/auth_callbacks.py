from telegram import Update
from telegram.ext import ContextTypes
from src.bot.conversations.auth_states import AuthState


# src/bot/conversations/auth_callbacks.py
from telegram import Update
from telegram.ext import ContextTypes


async def auth_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[HANDLER] auth_choice_callback")
    query = update.callback_query
    await query.answer()

    # 🆕 NUEVO JUGADOR
    if query.data == "auth:new":
        context.user_data.clear()

        context.user_data["auth_flow"] = "register"
        context.user_data["register_step"] = "username"
        context.user_data["register_data"] = {}

        await query.edit_message_text(
            "Perfecto 👌\n"
            "Vamos a crear tu usuario.\n\n"
            "👤 Decime qué username querés usar:"
        )

    # 🔑 USUARIO EXISTENTE
    elif query.data == "auth:existing":
        context.user_data.clear()

        context.user_data["auth_flow"] = "login"
        context.user_data["login_step"] = "username"
        context.user_data["login_data"] = {}

        await query.edit_message_text(
            "🔑 Vincular cuenta existente\n\n"
            "👤 Ingresá tu username:"
        )
