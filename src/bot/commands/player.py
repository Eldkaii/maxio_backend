from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.api_clients.users_api import UsersAPIClient
from src.services.player_service import generate_player_card_for_telegram_bot

users_api = UsersAPIClient()


def player_info_keyboard(username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="ℹ️ Más información",
                callback_data=f"player_info:{username}"
            )
        ]
    ])


async def player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usá el comando así:\n/player <username>"
        )
        return

    username = context.args[0]

    try:

        # 2️⃣ Generar carta (sin pasar template_path)
        card_buffer = generate_player_card_for_telegram_bot(username)


        # 3️⃣ Enviar imagen
        await update.message.reply_photo(
            photo=card_buffer,
            caption=f"🏅 Carta de {username}"
        )

        # 4️⃣ Enviar texto + botón
        await update.message.reply_text(
            "¿Querés ver más información de este jugador?",
            reply_markup=player_info_keyboard(username)
        )

    except Exception as e:
        await update.message.reply_text(
            f"Ocurrió un error al obtener la información del jugador 😕\n{e}"
        )


async def player_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "📊 Próximamente vas a poder ver más información del jugador."
    )
