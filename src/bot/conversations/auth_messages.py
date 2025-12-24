# src/bot/conversations/auth_messages.py
from telegram import Update
from telegram.ext import ContextTypes

from src.api_clients.auth_api import AuthAPIClient
from src.api_clients.users_api import UsersAPIClient
from src.models import TelegramIdentity
from src.schemas.user_schema import UserCreate
from src.services.telegram_identity_service import link_identity_to_user, create_identity_if_not_exists, \
    get_identity_by_telegram_user_id
from src.database import get_db
from src.config import settings


async def auth_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    auth_flow = context.user_data.get("auth_flow")

    # 🔐 LOGIN
    if auth_flow == "login":
        await process_login(update, context)
        return

    # 🆕 REGISTER
    if auth_flow == "register":
        await process_registration(update, context)
        return

    # ❓ SIN CONTEXTO
    await update.message.reply_text("Usá /start para comenzar.")


# =========================
# 🆕 REGISTRO
# =========================
async def process_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = context.user_data.get("register_step")

    # 1️⃣ USERNAME
    if step == "username":
        context.user_data["register_data"] = {
            "username": text
        }
        context.user_data["register_step"] = "email"

        await update.message.reply_text("📧 Ahora ingresá tu email:")
        return

    # 2️⃣ EMAIL
    if step == "email":
        context.user_data["register_data"]["email"] = text
        context.user_data["register_step"] = "password"

        await update.message.reply_text("🔒 Ahora elegí una contraseña:")
        return

    # 3️⃣ PASSWORD → REGISTER
    if step == "password":
        context.user_data["register_data"]["password"] = text

        await update.message.reply_text("⏳ Creando usuario...")

        payload = UserCreate(
            username=context.user_data["register_data"]["username"],
            email=context.user_data["register_data"]["email"],
            password=context.user_data["register_data"]["password"],
            is_bot=False,
        )

        try:
            api = UsersAPIClient()
            user = api.register_user(payload)

            db = next(get_db())

            # 🔹 1. Obtener o crear la identidad de Telegram
            identity = get_identity_by_telegram_user_id(
                db=db,
                telegram_user_id=update.effective_user.id
            )

            if not identity:
                identity = TelegramIdentity(
                    telegram_user_id=update.effective_user.id,
                    is_active=True
                )
                db.add(identity)
                db.commit()
                db.refresh(identity)

            # 🔹 2. Vincular identidad con usuario
            link_identity_to_user(
                db=db,
                identity=identity,
                user=user
            )

            await update.message.reply_text(
                f"✅ Usuario creado con éxito.\n"
                f"Bienvenido {user['username']} 🎉"
            )

            context.user_data.clear()

        except Exception as e:
            await update.message.reply_text(
                f"❌ Error {e} al crear el usuario.\n\n"
                "Probemos de nuevo.\n"
                "👤 Ingresá un username:"
            )

            context.user_data["register_step"] = "username"
            context.user_data["register_data"] = {}

# =========================
# 🔐 LOGIN
# =========================
async def process_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = context.user_data.get("login_step")

    db = next(get_db())

    # 1️⃣ USERNAME
    if step == "username":
        context.user_data["login_data"] = {"username": text}
        context.user_data["login_step"] = "password"

        await update.message.reply_text("🔐 Ingresá tu password:")
        return

    # 2️⃣ PASSWORD
    if step == "password":
        context.user_data["login_data"]["password"] = text

        try:
            # 🔑 Validar credenciales
            auth_api = AuthAPIClient(settings.api_root_login)
            token = auth_api.login(
                username=context.user_data["login_data"]["username"],
                password=context.user_data["login_data"]["password"]
            )

            # 🔎 Obtener información del player
            users_api = UsersAPIClient(token)
            user = users_api.get_user()

            # 📌 Obtener o crear identidad de Telegram
            identity = create_identity_if_not_exists(
                db=db,
                telegram_user_id=update.effective_user.id,
                telegram_username=update.effective_user.username
            )

            # 🔗 Vincular identidad al usuario
            link_identity_to_user(
                db=db,
                identity=identity,
                user=user  # user debe ser un objeto que tenga .id y .username
            )

            await update.message.reply_text(
                f"✅ Bienvenido de nuevo, {user['username']} 👋"
            )

            # 🧹 Limpiar contexto
            context.user_data.clear()

        except Exception as e:
            await update.message.reply_text(
                f"❌ Usuario o contraseña incorrectos.\n\n{str(e)}\n\n"
                "👤 Probemos de nuevo.\nIngresá tu username:"
            )
            context.user_data["login_step"] = "username"
            context.user_data["login_data"] = {}
