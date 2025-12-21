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

from src.config import settings
from src.utils.logger_config import app_logger as logger
from src.bot.handlers import register_handlers
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

    # 🔒 Esperar a que FastAPI esté lista
    wait_for_api()

    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers generales
    register_handlers(app)

    # /start
    app.add_handler(CommandHandler("start", start))

    # Callbacks (botones)
    app.add_handler(
        CallbackQueryHandler(auth_choice_callback, pattern="^auth:")
    )

    # Mensajes de texto
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, auth_message_handler)
    )

    logger.info("Bot iniciado. Esperando mensajes...")
    app.run_polling()
