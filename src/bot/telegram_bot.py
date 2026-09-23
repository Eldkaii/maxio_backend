# src/bot/telegram_bot.py

import time
import httpx
import asyncio
from telegram import MenuButtonDefault, MenuButtonWebApp, WebAppInfo
from telegram.ext import ApplicationBuilder
from src.bot.telegram_sender import TelegramNotificationSender
from src.bot.telegram_worker import notification_worker
from src.config import settings
from src.database import SessionLocal
from src.models.telegram_identity import TelegramIdentity
from src.utils.logger_config import app_logger as logger
from src.bot.telegram_handlers import get_handlers
from src.services.web_app_readiness import public_web_app_is_ready

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


async def start_notification_worker(application) -> None:
    """Inicia el worker cuando el loop de Telegram ya está disponible."""
    sender = TelegramNotificationSender(application)
    application.create_task(notification_worker_loop(sender), name="notification-worker")


async def _configure_mini_app_when_ready(application, web_app_url: str, is_temporary: bool) -> None:
    while not await public_web_app_is_ready(web_app_url):
        logger.warning("Mini App URL is still unavailable; retrying in 10 seconds")
        await asyncio.sleep(10)
    await configure_mini_app(application, web_app_url, is_temporary, verify_public_url=False)


async def configure_mini_app(
    application,
    web_app_url: str | None,
    is_temporary: bool = False,
    verify_public_url: bool = True,
) -> None:
    application.bot_data["web_app_url"] = web_app_url
    application.bot_data["web_app_is_temporary"] = is_temporary
    application.bot_data["web_app_ready"] = False
    """Expone la web local publicada por el túnel como Mini App del bot."""
    if not web_app_url:
        await clear_mini_app(application)
        logger.warning("Mini App no configurada: no hay URL HTTPS pública disponible")
        return
    if verify_public_url and not await public_web_app_is_ready(web_app_url):
        await clear_mini_app(application)
        logger.warning("Mini App not published until its public URL becomes reachable")
        application.create_task(
            _configure_mini_app_when_ready(application, web_app_url, is_temporary),
            name="wait-for-mini-app-url",
        )
        return
    try:
        menu_button = MenuButtonWebApp(
            text="Abrir Max_io",
            web_app=WebAppInfo(url=web_app_url),
        )
        await application.bot.set_chat_menu_button(menu_button=menu_button)
        for chat_id in _active_telegram_chat_ids():
            await application.bot.set_chat_menu_button(
                chat_id=chat_id,
                menu_button=menu_button,
            )
        logger.info("Mini App de Telegram configurada: %s", web_app_url)
        application.bot_data["web_app_ready"] = True
    except Exception:
        logger.exception("No se pudo configurar el botón de Mini App en Telegram")


async def clear_mini_app(application) -> None:
    """Evita que Telegram conserve un enlace de Quick Tunnel ya vencido."""
    try:
        await application.bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        for chat_id in _active_telegram_chat_ids():
            await application.bot.set_chat_menu_button(
                chat_id=chat_id,
                menu_button=MenuButtonDefault(),
            )
        logger.info("Botón temporal de Mini App removido")
    except Exception:
        logger.exception("No se pudo remover el botón temporal de Mini App")


def _active_telegram_chat_ids() -> list[int]:
    """Usuarios conocidos a los que se les fuerza el menú actual del túnel."""
    db = SessionLocal()
    try:
        return [
            int(telegram_user_id)
            for (telegram_user_id,) in db.query(TelegramIdentity.telegram_user_id)
            .filter(TelegramIdentity.is_active.is_(True))
            .all()
        ]
    finally:
        db.close()


async def post_init(application, web_app_url: str | None, is_temporary: bool = False) -> None:
    await start_notification_worker(application)
    await configure_mini_app(application, web_app_url, is_temporary)

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


def run_bot(web_app_url: str | None = None, is_temporary: bool = False):
    global telegram_app
    wait_for_api()

    logger.info("Inicializando bot de Telegram...")
    telegram_app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(lambda application: post_init(application, web_app_url, is_temporary))
        .post_shutdown(clear_mini_app)
        .build()
    )

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

    # ⚡ Arrancar polling
    logger.info("Bot iniciado. Esperando mensajes...")
    telegram_app.run_polling()
