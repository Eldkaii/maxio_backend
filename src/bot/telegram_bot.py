# src/bot/telegram_bot.py

import time
import httpx
import asyncio
from telegram.ext import ApplicationBuilder
from src.bot.telegram_sender import TelegramNotificationSender
from src.bot.telegram_worker import notification_worker
from src.config import settings
from src.utils.logger_config import app_logger as logger
from src.bot.telegram_handlers import get_handlers

TOKEN = settings.TELEGRAM_TOKEN
telegram_app: ApplicationBuilder | None = None  # variable global


def get_telegram_app() -> ApplicationBuilder:
    if telegram_app is None:
        raise RuntimeError("Bot de Telegram no inicializado aún")
    return telegram_app

async def notification_worker_loop(sender):
    while True:
        await notification_worker(sender)
        await asyncio.sleep(5)

def wait_for_api():
    """
    Bloquea el inicio del bot hasta que la API esté disponible.
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
    global telegram_app
    wait_for_api()

    logger.info("Inicializando bot de Telegram...")
    telegram_app = ApplicationBuilder().token(TOKEN).build()
    telegram_sender = TelegramNotificationSender(telegram_app)

    # Obtener handlers
    handlers = get_handlers()

    # Registrar handlers
    for cmd in handlers["commands"]:
        telegram_app.add_handler(cmd)
    for conv in handlers["conversations"]:
        telegram_app.add_handler(conv)
    for cb in handlers["callbacks"]:
        telegram_app.add_handler(cb)
    for msg in handlers["messages"]:
        telegram_app.add_handler(msg)

    # ⚡ Levantar worker en job_queue
    telegram_app.job_queue.run_once(lambda _: asyncio.create_task(notification_worker_loop(telegram_sender)), when=0)

    # ⚡ Arrancar polling
    logger.info("Bot iniciado. Esperando mensajes...")
    telegram_app.run_polling()
