from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters

# =========================
# Handlers de comandos
# =========================
from src.bot.commands.debug import whoami
from src.bot.commands.logout import logout_command
from src.bot.commands.player import (
    player_info_callback,
    player_command,
    photo_command,
)

# /start + auth (NO conversación)
from src.bot.commands.start import start, auth_choice_callback

# Conversaciones reales
from src.bot.conversations.new_match import new_match_conversation

# Callbacks que NO pertenecen a conversaciones
from src.bot.conversations.match_evaluation_callbacks import (
    process_match_result_callback,
)

from src.bot.conversations.profile_callbacks import (
    profile_view_player_selected,
    profile_view_callback,
)

# Mensajes de auth (username / password)
from src.bot.conversations.auth_messages import auth_message_handler

# Handler de fotos
from src.bot.bot_handlers.player_handler import handle_profile_photo


def get_handlers():
    """
    Devuelve listas de handlers para registrar en el bot.
    """
    return {
        "commands": [
            CommandHandler("start", start),
            CommandHandler("whoami", whoami),
            CommandHandler("player", player_command),
            CommandHandler("foto", photo_command),
            CommandHandler("logout", logout_command),

        ],
        "conversations": [
            # SOLO conversaciones reales
            new_match_conversation,
        ],
        "callbacks": [
            # Auth
            CallbackQueryHandler(auth_choice_callback, pattern="^auth:"),

            # Callbacks fuera de conversaciones
            CallbackQueryHandler(profile_view_callback, pattern="^profile:view$"),
            CallbackQueryHandler(profile_view_player_selected, pattern="^profile:view:.+"),
            CallbackQueryHandler(player_info_callback, pattern="^player_info:"),
            CallbackQueryHandler(process_match_result_callback, pattern="^match_result:"),
        ],
        "messages": [
            # Auth (texto plano)
            MessageHandler(filters.TEXT & ~filters.COMMAND, auth_message_handler),

            # Otros mensajes no conversacionales
            MessageHandler(filters.PHOTO, handle_profile_photo),
        ],
    }
