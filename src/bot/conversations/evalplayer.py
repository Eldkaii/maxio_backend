from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler

from src.bot.bot_handlers.evalplayer_handler import evalplayer_callback
from src.bot.commands.evalplayer import SELECT_BUTTONS, evalplayer_start

evalplayer_conversation = ConversationHandler(
    entry_points=[CommandHandler("evalplayer", evalplayer_start)],
    states={
        SELECT_BUTTONS: [CallbackQueryHandler(evalplayer_callback, pattern=r"^eval:")]
    },
    fallbacks=[]
)