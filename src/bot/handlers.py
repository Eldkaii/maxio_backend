# src/bot/bot_handlers.py

from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler,filters

from src.bot.commands.debug import whoami
from src.bot.commands.start import start, start_conversation
from src.bot.commands.player import player_command, player_info_callback, photo_command
from src.bot.bot_handlers.player_handler import handle_profile_photo
from src.bot.conversations.new_match import new_match_conversation
from src.bot.conversations.profile_callbacks import profile_view_callback, profile_view_player_selected, \
    profile_view_text_handler


def register_handlers(app):

    # 🔐 AUTH
    app.add_handler(start_conversation)

    # 🧪 debug
    app.add_handler(CommandHandler("whoami", whoami))

    # 👤 profile / player
    app.add_handler(CallbackQueryHandler(profile_view_callback, pattern="^profile:view$"))
    app.add_handler(CallbackQueryHandler(profile_view_player_selected, pattern="^profile:view:.+"))
    app.add_handler(CommandHandler("player", player_command))
    app.add_handler(CallbackQueryHandler(player_info_callback, pattern="^player_info:"))

    # 📷 fotos
    app.add_handler(CommandHandler("foto", photo_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_profile_photo))

    # ⚽ matches
    app.add_handler(new_match_conversation)

    # 🧹 TEXTO GENÉRICO (ÚLTIMO SIEMPRE)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, profile_view_text_handler)
    )
