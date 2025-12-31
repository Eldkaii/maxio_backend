# src/bot/callbacks/profile_callbacks.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# src/bot/callbacks/profile_callbacks.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import requests

from src.bot.commands.player import player_command
from src.config import Settings
from src.database import get_db
from src.services.telegram_identity_service import get_identity_by_telegram_user_id


async def profile_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    token = context.user_data.get("token")
    if not token:
        await query.edit_message_text(
            "🔒 Tu sesión expiró. Usá /start para iniciar sesión nuevamente."
        )
        return

    db = next(get_db())
    identity = get_identity_by_telegram_user_id(
        db=db,
        telegram_user_id=update.effective_user.id
    )

    if not identity or not identity.user:
        await query.edit_message_text("❌ No se pudo obtener tu usuario.")
        return

    username = identity.user.username
    headers = {"Authorization": f"Bearer {token}"}

    # ------------------------
    # Obtener top teammates
    # ------------------------
    teammates = []
    try:
        resp = requests.get(
            f"{Settings.API_BASE_URL}/player/{username}/top_teammates",
            headers=headers,
            params={"limit": 3},
            timeout=5
        )
        if resp.ok:
            teammates = resp.json()
    except Exception:
        pass

    # ------------------------
    # Mensaje base (SIEMPRE)
    # ------------------------
    await query.message.reply_text(
        "🔍 *Ver jugador*\n\n"
        "✍️ Escribí el *username* de un jugador para ver su perfil.",
        parse_mode="Markdown"
    )

    # ------------------------
    # Sin sugerencias
    # ------------------------
    if not teammates:
        await query.message.reply_text(
            "_Jugá partidos con tus amigos para que aparezcan aquí_",
            parse_mode="Markdown"
        )
        context.user_data["awaiting_player_username"] = True
        return

    # ------------------------
    # Con sugerencias
    # ------------------------
    keyboard = [
        [
            InlineKeyboardButton(
                f"👤 {p['name']} (ELO {p['elo']})",
                callback_data=f"profile:view:{p['name']}"
            )
        ]
        for p in teammates
    ]

    await query.message.reply_text(
        "👥 *Jugadores con los que más jugás:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    context.user_data["awaiting_player_username"] = True


async def profile_view_player_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    username = query.data.split(":")[2]

    # Ejecutamos el comando /player
    context.args = [username]
    await player_command(update, context)

    # Limpiar estado
    context.user_data.pop("awaiting_player_username", None)

    # Volver al menú principal
    from src.bot.conversations.auth_messages import send_post_auth_menu
    await send_post_auth_menu(update, context)


async def profile_view_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_player_username"):
        return

    username = update.message.text.strip()
    if not username:
        return

    # Ejecutar comando /player
    context.args = [username]
    await player_command(update, context)

    # Limpiar estado
    context.user_data.pop("awaiting_player_username", None)

    # Volver al menú principal
    from src.bot.conversations.auth_messages import send_post_auth_menu
    await send_post_auth_menu(update, context)
