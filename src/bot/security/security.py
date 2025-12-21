from src.services.telegram_user_service import get_telegram_user

async def authenticate(update):
    tg_user = update.effective_user
    if not tg_user:
        return None

    return get_telegram_user(tg_user.id)