# src/bot/bot_handlers.py

from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler,filters

from src.bot.commands.debug import whoami
from src.bot.commands.start import start
from src.bot.commands.player import player_command, player_info_callback, photo_command
from src.bot.bot_handlers.player_handler import handle_profile_photo
from src.bot.conversations.new_match import new_match_conversation


def register_handlers(app):
    #app.add_handler(CommandHandler("start", start))

    # 🧪 comandos de debug
    app.add_handler(CommandHandler("whoami", whoami))

    app.add_handler(CommandHandler("player", player_command))
    app.add_handler(
        CallbackQueryHandler(player_info_callback, pattern="^player_info:")
    )

    app.add_handler(CommandHandler("foto", photo_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_profile_photo))

 # -----------------------------
    # Comandos de match
    # -----------------------------
    app.add_handler(new_match_conversation)