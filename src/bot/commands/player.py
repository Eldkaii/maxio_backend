from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import requests


from src.api_clients.users_api import UsersAPIClient
from src.database import get_db
from src.config import Settings
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
    # Determinar cuál "message" usar: puede ser update.message o update.callback_query.message
    message = update.message or update.callback_query.message

    if not context.args:
        await message.reply_text(
            "Usá el comando así:\n/player <username>"
        )
        return

    username = context.args[0]

    try:
        # 2️⃣ Generar carta (sin pasar template_path)
        card_buffer = generate_player_card_for_telegram_bot(username)

        # 3️⃣ Enviar imagen
        await message.reply_photo(
            photo=card_buffer,
            caption=f"🏅 Carta de {username}"
        )

        # 4️⃣ Enviar texto + botón
        await message.reply_text(
            "¿Querés ver más información de este jugador?",
            reply_markup=player_info_keyboard(username)
        )

    except Exception as e:
        await message.reply_text(
            f"Ocurrió un error al obtener la información del jugador 😕\n{e}"
        )



async def player_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    username = query.data.split(":")[1]

    try:
        resp = requests.get(f"{Settings.API_BASE_URL}/player/{username}/profile", timeout=5)
        if resp.status_code != 200:
            await query.message.reply_text(
                f"❌ No se pudo obtener la información de {username}.\nStatus: {resp.status_code}"
            )
            return

        profile = resp.json()
        text_lines = []

        # =====================
        # Información básica
        # =====================
        text_lines.append(f"📊 *{profile['name']}* {'🤖' if profile['is_bot'] else ''}")
        text_lines.append(f"🏆 Partidos jugados: *{profile['cant_partidos']}*\n")

        # =====================
        # Stats individuales
        # =====================
        stats = profile["stats"]
        text_lines.append("⚡ *Estadísticas:*")
        text_lines.append(
            f"• Tiro: *{stats['tiro']:.1f}* | Ritmo: *{stats['ritmo']:.1f}* | Físico: *{stats['fisico']:.1f}*"
        )
        text_lines.append(
            f"• Defensa: *{stats['defensa']:.1f}* | Aura: *{stats['aura']:.1f}* | ELO: *{stats['elo']}*\n"
        )

        # =====================
        # Resumen de partidos
        # =====================
        summary = profile["matches_summary"]
        winrate_percent = summary["winrate"] * 100
        text_lines.append("📈 *Resumen de partidos:*")
        text_lines.append(
            f"• Jugados: *{summary['played']}* | Ganados: *{summary['won']}* | Winrate: *{winrate_percent:.1f}%*\n"
        )

        # =====================
        # Últimos partidos
        # =====================
        recent_matches = profile.get("recent_matches", [])[:5]
        if recent_matches:
            text_lines.append("⏱ *Últimos partidos:*")
            for m in recent_matches:
                date = m["date"].split("T")[0]
                result_emoji = "✅" if m["result"] == "win" else "❌" if m["result"] == "loss" else "⏳"
                teammates = ", ".join([t["name"] for t in m["teammates"]])
                opponents = ", ".join([o["name"] for o in m["opponents"]])
                text_lines.append(
                    f"• {date} | {result_emoji}\n   Con: {teammates}\n   Contra: {opponents}\n"
                )

        # =====================
        # Relaciones
        # =====================
        relations = profile.get("relations", {})
        text_lines.append("🤝 *Relaciones destacadas:*")
        most_played = ", ".join([p["name"] for p in relations.get("most_played_with", [])]) or "Ninguno"
        top_allies = ", ".join([p["name"] for p in relations.get("top_allies", [])]) or "Ninguno"
        top_opponents = ", ".join([p["name"] for p in relations.get("top_opponents", [])]) or "Ninguno"
        text_lines.append(f"• Jugadores frecuentes: {most_played}")
        text_lines.append(f"• Mejores aliados: {top_allies}")
        text_lines.append(f"• Principales rivales: {top_opponents}")

        # =====================
        # Enviar mensaje
        # =====================
        await query.message.reply_text(
            "\n".join(text_lines),
            parse_mode="Markdown"
        )

    except Exception as e:
        await query.message.reply_text(
            f"❌ Ocurrió un error al obtener la información de {username}.\n{e}"
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


