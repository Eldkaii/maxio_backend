# src/bot/debug/update_logger.py
from telegram import Update
from telegram.ext import ContextTypes

async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        msg = update.message
        if msg.text:
            print(
                f"[UPDATE] TEXT | user={msg.from_user.id} "
                f"username={msg.from_user.username} "
                f"text='{msg.text}'"
            )
        elif msg.photo:
            print(
                f"[UPDATE] PHOTO | user={msg.from_user.id} "
                f"username={msg.from_user.username}"
            )

    elif update.callback_query:
        cq = update.callback_query
        print(
            f"[UPDATE] CALLBACK | user={cq.from_user.id} "
            f"username={cq.from_user.username} "
            f"data='{cq.data}'"
        )
