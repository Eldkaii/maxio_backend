from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler
import requests

from src.services.telegram_identity_service import (
    create_identity_if_not_exists,
    is_identity_linked,
    get_identity_by_telegram_user_id,
)
from src.database import get_db
from src.config import Settings

ASK_PASSWORD = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if tg_user is None:
        return ConversationHandler.END

    db = next(get_db())

    # Creamos o recuperamos la identidad de Telegram
    identity = create_identity_if_not_exists(
        db=db,
        telegram_user_id=tg_user.id,
        telegram_username=tg_user.username
    )

    # Guardamos identity en el context
    context.user_data["identity"] = identity

    # Si el usuario ya está vinculado
    if is_identity_linked(identity):
        await update.message.reply_text(
            f"👋 Bienvenido {identity.user.username}.\n"
            "Para iniciar sesión en Max_io, escribí tu contraseña:"
        )
        return ASK_PASSWORD

    # Si no está vinculado, mostramos opciones de registro
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
    return ConversationHandler.END


async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    identity = context.user_data.get("identity")

    if not identity or not identity.user:
        await update.message.reply_text("🔗 Primero vinculá tu cuenta con /start.")
        return ConversationHandler.END

    username = identity.user.username

    # Llamamos al endpoint de login
    try:
        response = requests.post(
            f"{Settings.API_BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=5
        )
        if response.status_code != 200:
            await update.message.reply_text("❌ Usuario o contraseña incorrectos.")
            return ASK_PASSWORD

        token = response.json().get("access_token")
        if not token:
            await update.message.reply_text("❌ Error al obtener token.")
            return ASK_PASSWORD

        # Guardamos token en context
        context.user_data["token"] = token

        await update.message.reply_text(f"✅ Sesión iniciada. ¡Bienvenido {username}!")

    except requests.RequestException:
        await update.message.reply_text("❌ Error de conexión al backend. Intentá más tarde.")
        return ConversationHandler.END

    return ConversationHandler.END


# Conversación completa para /start
start_conversation = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_PASSWORD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)
        ]
    },
    fallbacks=[]
)
