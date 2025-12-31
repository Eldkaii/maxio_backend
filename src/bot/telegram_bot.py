# src/bot/telegram_bot.py

import time
import httpx

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from src.bot.bot_handlers.player_handler import handle_profile_photo
from src.bot.commands.debug import whoami
from src.bot.commands.player import player_info_callback, player_command, photo_command
from src.bot.commands.start import start_conversation
from src.bot.conversations.new_match import new_match_conversation
from src.bot.conversations.profile_callbacks import profile_view_player_selected, profile_view_callback, \
    profile_view_text_handler
from src.config import settings
from src.utils.logger_config import app_logger as logger
from src.bot.conversations.auth_messages import auth_message_handler
from src.bot.conversations.auth_callbacks import auth_choice_callback

TOKEN = "8303933517:AAGsbPhx7QYyJLshY7yqsz4gt56yvNWXGV0"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Max_io bot activo 🚀")


def wait_for_api():
    """
    Bloquea el inicio del bot hasta que la API esté disponible.
    Evita errores de conexión al registrar usuarios.
    """
    health_url = f"{settings.api_root}"

    logger.info("Esperando a que la API esté disponible...")

    while True:
        try:
            response = httpx.get(health_url, timeout=2)
            if response.status_code == 200:
                logger.info("API disponible, iniciando bot.")
                break
        except Exception:
            logger.info("API no disponible aún, reintentando...")
            time.sleep(1)


def run_bot():
    logger.info("Inicializando bot de Telegram...")
    wait_for_api()

    app = ApplicationBuilder().token(TOKEN).build()

    # =========================
    # CONVERSACIONES (PRIMERO SIEMPRE)
    # =========================
    app.add_handler(start_conversation)
    app.add_handler(new_match_conversation)

    # =========================
    # CALLBACKS DE MENÚ
    # =========================

    app.add_handler(
        CallbackQueryHandler(auth_choice_callback, pattern="^auth:")
    )

    app.add_handler(
        CallbackQueryHandler(profile_view_callback, pattern="^profile:view$")
    )

    app.add_handler(
        CallbackQueryHandler(
            profile_view_player_selected,
            pattern="^profile:view:.+"
        )
    )

    app.add_handler(
        CallbackQueryHandler(player_info_callback, pattern="^player_info:")
    )

    # =========================
    # COMANDOS
    # =========================
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("player", player_command))
    app.add_handler(CommandHandler("foto", photo_command))

    # =========================
    # MENSAJES ESPECÍFICOS
    # =========================
    app.add_handler(
        MessageHandler(filters.PHOTO, handle_profile_photo)
    )

    # =========================
    # TEXTO CONTEXTUAL (ANTES)
    # =========================
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            profile_view_text_handler
        )
    )

    # =========================
    # TEXTO AUTH / FALLBACK (ÚLTIMO SIEMPRE)
    # =========================
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            auth_message_handler
        )
    )

    logger.info("Bot iniciado. Esperando mensajes...")
    app.run_polling()
