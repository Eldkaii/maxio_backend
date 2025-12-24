# src/bot/handlers.py

from telegram.ext import CommandHandler,CallbackQueryHandler

from src.bot.commands.debug import whoami
from src.bot.commands.start import start
from src.bot.commands.player import player_command, player_info_callback

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))

    # 🧪 comandos de debug
    app.add_handler(CommandHandler("whoami", whoami))

    app.add_handler(CommandHandler("player", player_command))
    app.add_handler(
        CallbackQueryHandler(player_info_callback, pattern="^player_info:")
    )