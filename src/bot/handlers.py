# src/bot/handlers.py

from telegram.ext import CommandHandler

from src.bot.commands.debug import whoami
from src.bot.commands.start import start

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))

    # 🧪 comandos de debug
    app.add_handler(CommandHandler("whoami", whoami))
