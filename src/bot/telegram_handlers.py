# src/bot/telegram_handlers.py

from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Handlers de comandos
from src.bot.commands.debug import whoami
from src.bot.commands.player import player_info_callback, player_command, photo_command
from src.bot.commands.start import start_conversation

# Conversaciones
from src.bot.conversations.new_match import new_match_conversation
from src.bot.conversations.match_evaluation_callbacks import process_match_result_callback

# Callbacks de perfil
from src.bot.conversations.profile_callbacks import (
    profile_view_player_selected,
    profile_view_callback,
    profile_view_text_handler
)

# Callbacks de auth
from src.bot.conversations.auth_messages import auth_message_handler
from src.bot.conversations.auth_callbacks import auth_choice_callback

# Handler de fotos
from src.bot.bot_handlers.player_handler import handle_profile_photo

# Debug de updates
from src.bot.debug.update_logger import log_update


def get_handlers():
    """
    Devuelve listas de handlers para registrar en el bot.
    """
    return {
        "commands": [
            CommandHandler("whoami", whoami),
            CommandHandler("player", player_command),
            CommandHandler("foto", photo_command),
        ],
        "conversations": [
            start_conversation,
            new_match_conversation,
        ],
        "callbacks": [
            CallbackQueryHandler(auth_choice_callback, pattern="^auth:"),
            CallbackQueryHandler(profile_view_callback, pattern="^profile:view$"),
            CallbackQueryHandler(profile_view_player_selected, pattern="^profile:view:.+"),
            CallbackQueryHandler(player_info_callback, pattern="^player_info:"),
            CallbackQueryHandler(process_match_result_callback, pattern="^match_result:"),
        ],
        "messages": [
            MessageHandler(filters.ALL, log_update),
            MessageHandler(filters.PHOTO, handle_profile_photo),
            MessageHandler(filters.TEXT & ~filters.COMMAND, auth_message_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, profile_view_text_handler),
        ],
    }
