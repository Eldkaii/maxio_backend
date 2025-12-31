from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
)
from io import BytesIO
import requests
from src.config import Settings
from src.database import get_db
from src.services.telegram_identity_service import (
    get_identity_by_telegram_user_id,
    is_identity_linked,
)

from datetime import datetime

# Estados
MATCH_ADD_PLAYERS = 0
MATCH_ADD_GROUP = 1
MATCH_ADD_INDIVIDUALS = 2


# ------------------------
# /new_match
# ------------------------
async def new_match_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = next(get_db())

    identity = get_identity_by_telegram_user_id(
        db=db,
        telegram_user_id=update.effective_user.id
    )

    if not identity or not is_identity_linked(identity):
        await update.message.reply_text(
            "❌ No estás logueado. Usá /start para iniciar sesión."
        )
        return ConversationHandler.END

    # ------------------------
    # Parsear fecha opcional
    # ------------------------
    match_date = None

    if context.args:
        date_str = " ".join(context.args)

        try:
            match_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            await update.message.reply_text(
                "❌ Formato de fecha inválido.\n\n"
                "Usá:\n"
                "`/new_match AAAA-MM-DD HH:MM`\n"
                "Ej: `/new_match 2025-01-15 22:30`",
                parse_mode="Markdown"
            )
            return ConversationHandler.END

    context.user_data["new_match"] = {
        "date": match_date,   # None o datetime
        "groups": [],
        "individuals": [],
    }

    await show_main_menu(update, context)
    return MATCH_ADD_PLAYERS



# ------------------------
# Menú principal
# ------------------------
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧩 Agregar grupo predefinido", callback_data="add:group")],
        [InlineKeyboardButton("👤 Agregar jugador(es) sueltos", callback_data="add:individual")],
        [InlineKeyboardButton("✅ Finalizar y crear match", callback_data="add:done")],
    ]

    await update.message.reply_text(
        "👥 Armá el partido:\n"
        "• Un *grupo predefinido* no se separa\n"
        "• Los *jugadores sueltos* se balancean libremente",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ------------------------
# Callback principal
# ------------------------
async def add_player_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]

    if action == "group":
        await query.message.reply_text(
            "✍️ Escribí los usernames del grupo (separados por espacios o comas):\n"
            "Ej: juan pedro lucas"
        )
        return MATCH_ADD_GROUP

    if action == "individual":
        await query.message.reply_text(
            "✍️ Escribí uno o más usernames:\n"
            "Ej: ana martin"
        )
        return MATCH_ADD_INDIVIDUALS

    if action == "done":
        return await finalize_match(query, context)

    return MATCH_ADD_PLAYERS


# ------------------------
# Agregar grupo predefinido
# ------------------------
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace(",", " ")
    usernames = [u.strip() for u in text.split() if u]

    if len(usernames) < 2:
        await update.message.reply_text(
            "⚠️ Un grupo debe tener al menos 2 jugadores."
        )
        return MATCH_ADD_PLAYERS

    context.user_data["new_match"]["groups"].append(usernames)

    await update.message.reply_text(
        f"✅ Grupo agregado: {', '.join(usernames)}"
    )

    await show_main_menu(update, context)
    return MATCH_ADD_PLAYERS


# ------------------------
# Agregar jugadores sueltos
# ------------------------
async def add_individuals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace(",", " ")
    usernames = [u.strip() for u in text.split() if u]

    if not usernames:
        await update.message.reply_text("⚠️ No ingresaste usernames válidos.")
        return MATCH_ADD_PLAYERS

    individuals = context.user_data["new_match"]["individuals"]

    added = []
    for u in usernames:
        if u not in individuals:
            individuals.append(u)
            added.append(u)

    if added:
        await update.message.reply_text(
            f"✅ Jugadores agregados: {', '.join(added)}"
        )

    await show_main_menu(update, context)
    return MATCH_ADD_PLAYERS


# ------------------------
# Finalizar y crear match
# ------------------------
async def finalize_match(query, context: ContextTypes.DEFAULT_TYPE):
    token = context.user_data.get("token")
    data = context.user_data["new_match"]

    if not data["groups"] and not data["individuals"]:
        await query.message.reply_text("❌ No agregaste jugadores al partido.")
        return MATCH_ADD_PLAYERS

    headers = {"Authorization": f"Bearer {token}"}

    # ------------------------
    # Crear match
    # ------------------------
    match_date = data.get("date")



    match_resp = requests.post(
        f"{Settings.API_BASE_URL}/match/matches",
        headers=headers,
        json={
            "date": match_date.isoformat() if match_date else None,
            "max_players": 10
        },
        timeout=5
    )

    if not match_resp.ok:
        await query.message.reply_text(
            f"❌ Error al crear el match:\n{match_resp.text}"
        )
        return ConversationHandler.END

    match_data = match_resp.json()
    match_id = match_data["id"]

    # ------------------------
    # Construir grupos de entrada
    # ------------------------
    input_groups = []
    input_groups.extend(data["groups"])
    input_groups.extend([[u] for u in data["individuals"]])

    # ------------------------
    # Agregar jugadores
    # ------------------------
    for group in input_groups:
        for username in group:
            player_resp = requests.get(
                f"{Settings.API_BASE_URL}/player/{username}",
                headers=headers,
                timeout=5
            )

            if not player_resp.ok:
                await query.message.reply_text(
                    f"⚠️ No se encontró el jugador {username}."
                )
                continue

            player = player_resp.json()

            requests.post(
                f"{Settings.API_BASE_URL}/match/matches/{match_id}/players/{player['id']}",
                headers=headers,
                timeout=5
            )

    # ------------------------
    # Enviar grupos predefinidos (si existen)
    # ------------------------
    if data["groups"]:
        requests.post(
            f"{Settings.API_BASE_URL}/match/matches/{match_id}/pre-set-groups",
            headers=headers,
            json={"groups": data["groups"]},
            timeout=5
        )

    await query.message.reply_text(
        f"✅ Match creado con ID {match_id}.\n"
        "⚔️ Generando equipos automáticamente..."
    )

    # ------------------------
    # Generar equipos
    # ------------------------
    try:
        resp = requests.post(
            f"{Settings.API_BASE_URL}/match/matches/{match_id}/generate-teams",
            headers=headers,
            timeout=5
        )

        if resp.ok:
            team_data = resp.json()
            summary = format_match_summary(team_data)

            await query.message.reply_text(
                "⚔️ Equipos generados automáticamente:\n\n" + summary,
                parse_mode="Markdown"
            )

            # ------------------------
            # Generar y enviar imagen del match
            # ------------------------
            try:
                img_resp = requests.post(
                    f"{Settings.API_BASE_URL}/match/matches/{match_id}/match-card",
                    headers=headers,
                    timeout=10
                )

                if img_resp.status_code != 200:
                    await query.message.reply_text(
                        "⚠️ El match se creó correctamente, pero no se pudo generar la imagen."
                    )
                else:
                    image_buffer = BytesIO(img_resp.content)
                    image_buffer.name = "match_card.png"

                    await query.message.reply_photo(
                        photo=image_buffer,
                        caption="🖼️ Resumen visual del match"
                    )

            except requests.RequestException as e:
                await query.message.reply_text(
                    f"⚠️ Error al obtener la imagen del match:\n{e}"
                )

        else:
            detail = resp.json().get("detail", resp.text)
            await query.message.reply_text(
                "❌ No se pudieron generar los equipos.\n"
                f"Detalle: {detail}"
            )

    except requests.RequestException as e:
        await query.message.reply_text(
            f"❌ Error de conexión con el backend:\n{e}"
        )

    return ConversationHandler.END


def format_match_summary(match: dict) -> str:
    lines = []

    lines.append("🎮 *Match creado*")
    lines.append("")
    lines.append(f"🆔 ID: `{match.get('id')}`")
    lines.append(f"📅 Fecha: {match.get('date')}")
    lines.append(f"👥 Máx jugadores: {match.get('max_players')}")
    lines.append("")

    def player_label(player: dict) -> str:
        return (
            player.get("username")
            or player.get("name")
            or player.get("display_name")
            or f"Player {player.get('id', '?')}"
        )

    def format_team(team: dict, emoji: str) -> list[str]:
        if not team:
            return [f"{emoji} Equipo: —"]

        name = escape_markdown(
            team.get("name") or f"Equipo {team.get('id')}"
        )
        players = team.get("players", [])

        team_lines = [f"{emoji} *{name}*"]

        if not players:
            team_lines.append("   • (sin jugadores)")
            return team_lines

        for p in players:
            player_name = escape_markdown(
                p.get("name") or f"Player {p.get('id', '?')}"
            )
            team_lines.append(f"   • {player_name}")

        return team_lines

    lines.extend(format_team(match.get("team1"), "🔵"))
    lines.append("")
    lines.extend(format_team(match.get("team2"), "🔴"))
    lines.append("")

    winner = match.get("winner_team")
    # if winner:
    #     winner_name = winner.get("name") or f"Equipo {winner.get('id')}"
    #     lines.append(f"🏆 Ganador: *{winner_name}*")
    # else:
    #     lines.append("🏆 Ganador: —")

    return "\n".join(lines)

def escape_markdown(text: str) -> str:
    if not text:
        return ""
    return (
        text
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
    )


# ------------------------
# Cancelar
# ------------------------
async def cancel_new_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_match", None)
    await update.message.reply_text("❌ Creación de partido cancelada.")
    return ConversationHandler.END
