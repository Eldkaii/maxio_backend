from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.api_clients.users_api import UsersAPIClient
from src.database import get_db
from src.services.player_service import generate_player_card_for_telegram_bot
from src.services.telegram_identity_service import is_identity_linked, get_identity_by_telegram_user_id

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

async def photo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = next(get_db())

    identity = get_identity_by_telegram_user_id(
        db=db,
        telegram_user_id=update.effective_user.id
    )

    if not identity or not is_identity_linked(identity):
        await update.message.reply_text(
            "❌ No estás logueado. Usá /start para iniciar sesión."
        )
        return

    # Marcamos que el próximo mensaje debe ser una foto
    context.user_data["awaiting_photo"] = True

    await update.message.reply_text(
        "📸 Enviame la foto que querés usar como perfil."
    )


