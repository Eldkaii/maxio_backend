from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from src.bot.conversations.auth_messages import send_post_auth_menu
from src.services.telegram_identity_service import (
    create_identity_if_not_exists,
    is_identity_linked,
)
from src.database import get_db


# =========================
# /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[COMMAND] /start")

    # 🔥 limpiar SOLO estado de auth
    for key in [
        "auth_flow",
        "register_step",
        "register_data",
        "login_step",
        "login_data",
    ]:
        context.user_data.pop(key, None)

    tg_user = update.effective_user
    if tg_user is None:
        return

    db = next(get_db())

    identity = create_identity_if_not_exists(
        db=db,
        telegram_user_id=tg_user.id,
        telegram_username=tg_user.username,
    )

    context.user_data["identity_id"] = identity.id

    # =========================
    # Usuario ya vinculado
    # =========================
    if is_identity_linked(identity):
        # 🔐 Siempre invalidar token previo (puede estar vencido)
        context.user_data.pop("token", None)

        # Preparar flujo de login
        context.user_data["auth_flow"] = "login"
        context.user_data["login_step"] = "password"
        context.user_data["login_data"] = {
            "username": identity.user.username
        }

        await update.message.reply_text(
            f"👋 Bienvenido {identity.user.username}.\n"
            "Para iniciar sesión en Max_io, escribí tu contraseña:"
        )
        return

    # =========================
    # Usuario NO vinculado
    # =========================
    keyboard = [
        [
            InlineKeyboardButton("🆕 Soy nuevo jugador", callback_data="auth:new"),
            InlineKeyboardButton("🔑 Ya tengo cuenta", callback_data="auth:existing"),
        ]
    ]

    await update.message.reply_text(
        "👋 Bienvenido a Max_io.\n\n¿Qué querés hacer?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# Callback auth
# =========================
async def auth_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[HANDLER] auth_choice_callback")

    query = update.callback_query
    await query.answer()

    # limpiar estado previo
    for key in [
        "auth_flow",
        "register_step",
        "register_data",
        "login_step",
        "login_data",
    ]:
        context.user_data.pop(key, None)

    # 🆕 REGISTRO
    if query.data == "auth:new":
        context.user_data["auth_flow"] = "register"
        context.user_data["register_step"] = "username"
        context.user_data["register_data"] = {}

        await query.edit_message_text(
            "Perfecto 👌\n"
            "Vamos a crear tu usuario.\n\n"
            "👤 Decime qué username querés usar:"
        )
        return

    # 🔑 LOGIN
    if query.data == "auth:existing":
        context.user_data["auth_flow"] = "login"
        context.user_data["login_step"] = "username"
        context.user_data["login_data"] = {}

        await query.edit_message_text(
            "🔑 Vincular cuenta existente\n\n"
            "👤 Ingresá tu username:"
        )
