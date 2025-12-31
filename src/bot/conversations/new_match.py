from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from src.bot.bot_handlers.new_match_handler import (
    new_match_command,
    cancel_new_match,
    add_player_callback,
    add_group,
    add_individuals,
    MATCH_ADD_PLAYERS,
    MATCH_ADD_GROUP,
    MATCH_ADD_INDIVIDUALS,
)

new_match_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("new_match", new_match_command),
        CallbackQueryHandler(new_match_command, pattern="^match:new_match$")
    ],
    states={
        MATCH_ADD_PLAYERS: [
            CallbackQueryHandler(add_player_callback, pattern="^add:")
        ],
        MATCH_ADD_GROUP: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_group)
        ],
        MATCH_ADD_INDIVIDUALS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_individuals)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_new_match),
    ],
    per_message=False,  # 🔥 ESTO ES LA CLAVE
)
