# src/bot/conversations/auth_messages.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.api_clients.auth_api import AuthAPIClient
from src.api_clients.users_api import UsersAPIClient
from src.models import TelegramIdentity
from src.schemas.user_schema import UserCreate
from src.services.telegram_identity_service import link_identity_to_user, create_identity_if_not_exists
from src.database import get_db
from src.config import settings


async def auth_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[HANDLER] auth_message_handler")

    auth_flow = context.user_data.get("auth_flow")

    # ⛔ si no estamos en login/registro, no interferir
    if auth_flow not in ("login", "register"):
        return

    if context.user_data.get("awaiting_player_username"):
        return

    if auth_flow == "login":
        await process_login(update, context)
        return

    if auth_flow == "register":
        await process_registration(update, context)
        return


# =========================
# 🆕 REGISTRO
# =========================
async def process_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = context.user_data.get("register_step")

    # 1️⃣ USERNAME
    if step == "username":
        context.user_data["register_data"] = {"username": text.lower()}
        context.user_data["register_step"] = "email"
        await update.message.reply_text("📧 Ahora ingresá tu email:")
        return

    # 2️⃣ EMAIL
    if step == "email":
        context.user_data["register_data"]["email"] = text
        context.user_data["register_step"] = "password"
        await update.message.reply_text("🔒 Ahora elegí una contraseña:")
        return

    # 3️⃣ PASSWORD → REGISTER + LOGIN
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
            # Crear usuario
            users_api = UsersAPIClient()
            users_api.register_user(payload)

            # Login automático
            auth_api = AuthAPIClient(settings.api_root_login)
            token = auth_api.login(username=payload.username, password=payload.password)

            # Guardar token
            context.user_data["token"] = token

            # Obtener usuario autenticado
            users_api = UsersAPIClient(token)
            user = users_api.get_user()

            # Crear o obtener identidad de Telegram
            db = next(get_db())
            identity = create_identity_if_not_exists(
                db=db,
                telegram_user_id=update.effective_user.id,
                telegram_username=update.effective_user.username
            )

            # Vincular identidad ↔ usuario
            link_identity_to_user(db=db, identity=identity, user=user)

            await update.message.reply_text(f"✅ Usuario creado con éxito.\nBienvenido {user['username']} 🎉")

            # Limpiar estado de registro
            for key in ["auth_flow", "register_step", "register_data"]:
                context.user_data.pop(key, None)

            await send_post_auth_menu(update, context)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Error al crear el usuario.\n\n{str(e)}\n"
                "Probemos de nuevo.\n👤 Ingresá un username:"
            )
            context.user_data["register_step"] = "username"
            context.user_data["register_data"] = {}


# =========================
# 🔐 LOGIN
# =========================
async def process_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("login_step")
    db = next(get_db())

    # Si la identidad ya tiene username, no sobrescribirlo
    if step == "username" and "username" not in context.user_data.get("login_data", {}):
        username = update.message.text.strip().lower()
        if not username:
            await update.message.reply_text("⚠️ Username inválido.")
            return "username"
        context.user_data["login_data"] = {"username": username}
        context.user_data["login_step"] = "password"
        await update.message.reply_text("🔐 Ingresá tu password:")
        return

    # PASSWORD
    if step == "password":
        password = update.message.text.strip()
        login_data = context.user_data.get("login_data")
        identity = create_identity_if_not_exists(
            db=db,
            telegram_user_id=update.effective_user.id,
            telegram_username=update.effective_user.username
        )

        try:
            # Validar credenciales
            auth_api = AuthAPIClient(settings.api_root_login)
            token = auth_api.login(username=login_data["username"], password=password)
            context.user_data["token"] = token

            # Obtener usuario autenticado
            users_api = UsersAPIClient(token)
            user = users_api.get_user()

            # Vincular identidad solo si no estaba vinculada
            if not identity.user_id:
                link_identity_to_user(db=db, identity=identity, user=user)

            await update.message.reply_text(f"✅ Bienvenido de nuevo, {user['username']} 👋")

            # Limpiar estado de login
            for key in ["auth_flow", "login_step", "login_data"]:
                context.user_data.pop(key, None)

            await send_post_auth_menu(update, context)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Usuario o contraseña incorrectos.\n\n{str(e)}\n"
                "👤 Probemos de nuevo.\nIngresá tu username:"
            )
            context.user_data["login_step"] = "username"
            context.user_data["login_data"] = {}


async def send_post_auth_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("📸 Agregar Foto de Perfil", callback_data="profile:add_photo")],
        [InlineKeyboardButton("👤 Ver Jugador", callback_data="profile:view")],
        [InlineKeyboardButton("⚔️ Crear Partido", callback_data="match:new_match")],
    ]

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="¿Qué querés hacer ahora?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
