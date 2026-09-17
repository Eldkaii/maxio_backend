from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from io import BytesIO
import requests

from src.bot.conversations.auth_messages import send_post_auth_menu
from src.config import Settings
from src.database import get_db
from src.services.telegram_identity_service import (
    get_identity_by_telegram_user_id,
    is_identity_linked,
)
from datetime import datetime

# ========================
# Estados
# ========================
MATCH_ADD_PLAYERS = 0
MATCH_ADD_GROUP = 1
MATCH_ADD_INDIVIDUALS = 2
MATCH_SELECT_TEAM_SIZE = 3

# ========================
# /new_match
# ========================
async def new_match_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = next(get_db())
    msg = update.effective_message

    identity = get_identity_by_telegram_user_id(
        db=db,
        telegram_user_id=update.effective_user.id
    )

    if not identity or not is_identity_linked(identity):
        await msg.reply_text(
            "❌ No estás logueado. Usá /start para iniciar sesión."
        )
        return ConversationHandler.END

    # Guardamos el username logueado para poder obtener top teammates
    context.user_data["logged_username"] = identity.user.username

    # Parsear fecha opcional
    match_date = None
    if context.args:
        date_str = " ".join(context.args)
        try:
            match_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            await msg.reply_text(
                "❌ Formato de fecha inválido.\n\n"
                "Usá:\n"
                "`/new_match AAAA-MM-DD HH:MM`\n"
                "Ej: `/new_match 2025-01-15 22:30`",
                parse_mode="Markdown"
            )
            return ConversationHandler.END

    context.user_data["new_match"] = {
        "date": match_date,
        "groups": [],
        "individuals": [],
    }

    # Inicializamos la UI dinámica
    await msg.reply_text(
        "¿Cuántos jugadores querés por equipo? Los lugares restantes se completarán con bots después de balancear sólo a los jugadores reales.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{size} por equipo", callback_data=f"team_size:{size}")]
            for size in range(2, 11)
        ]),
    )
    return MATCH_SELECT_TEAM_SIZE


async def select_team_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        team_size = int(query.data.removeprefix("team_size:"))
    except (AttributeError, ValueError):
        await query.message.reply_text("Elegí un tamaño de equipo válido.")
        return MATCH_SELECT_TEAM_SIZE
    if not 1 <= team_size <= 10:
        await query.message.reply_text("Elegí un tamaño de equipo entre 1 y 10.")
        return MATCH_SELECT_TEAM_SIZE

    context.user_data["new_match"]["team_size"] = team_size
    await query.edit_message_text(f"Tamaño elegido: {team_size} por equipo.")
    await init_match_ui(query, context, username=context.user_data["logged_username"])
    return MATCH_ADD_PLAYERS

# ========================
# UI dinámica de creación de match (versión estética)
# ========================
async def init_match_ui(update_or_query, context: ContextTypes.DEFAULT_TYPE, username: str | None = None):
    """Inicializa todos los mensajes de la creación de match y guarda sus IDs"""
    chat_id = (
        update_or_query.effective_chat.id
        if hasattr(update_or_query, "effective_chat")
        else update_or_query.message.chat.id
    )
    context.user_data["chat_id"] = chat_id  # Guardamos chat_id para notificaciones

    # 1️⃣ Mensaje explicativo
    info_msg = (
        "👥 *Armá el partido*\n"
        "────────────────────────\n"
        "• Un *grupo predefinido* no se separa\n"
        "• Los *jugadores sueltos* se balancean libremente\n"
        "• Podés agregar tus *top teammates* directamente\n"
        "────────────────────────"
    )

    # 2️⃣ Botones "Agregar grupo" y "Agregar jugador(es)" en la misma línea
    buttons_row = [
        InlineKeyboardButton("🧩 Agregar grupo", callback_data="add:group"),
        InlineKeyboardButton("👤 Agregar jugador(es)", callback_data="add:individual")
    ]
    buttons_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=info_msg,
        reply_markup=InlineKeyboardMarkup([buttons_row]),
        parse_mode="Markdown"
    )
    # Guardamos el message_id de los botones
    context.user_data["msg_group_btn_id"] = buttons_msg.message_id
    context.user_data["msg_individual_btn_id"] = buttons_msg.message_id

    # 3️⃣ Mensaje de jugadores agregados
    await update_added_players(update_or_query, context)

    # 4️⃣ Mensaje de notificaciones dinámicas
    msg_notify = await context.bot.send_message(
        chat_id=chat_id,
        text="ℹ️ *Acciones e información*\n────────────────────────",
        parse_mode="Markdown"
    )
    context.user_data["msg_notify_id"] = msg_notify.message_id

    # 5️⃣ Botones top teammates
    if username:
        await update_top_teammates(update_or_query, context, username)

    # 6️⃣ Botón finalizar + cancelar
    finalize_row = [
        InlineKeyboardButton("⚔️ Finalizar", callback_data="add:done"),
        InlineKeyboardButton("❌ Cancelar", callback_data="add:cancel_temp")
    ]

    finish_btn = await context.bot.send_message(
        chat_id=chat_id,
        text="────────────────────────\n✅ *Opciones finales*",
        reply_markup=InlineKeyboardMarkup([finalize_row]),
        parse_mode="Markdown"
    )
    context.user_data["msg_finish_id"] = finish_btn.message_id





# ========================
# Enviar o actualizar mensaje de jugadores agregados
# ========================
async def update_added_players(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    new_match = context.user_data.get("new_match", {})
    individuals = new_match.get("individuals", [])
    groups = new_match.get("groups", [])

    # Construir mensaje
    added_msg = "👥 *Jugadores actualmente agregados:*\n"
    for g in groups:
        escaped_group = [escape_markdown(u) for u in g]
        added_msg += "• " + ", ".join(escaped_group) + "\n"
    for i in individuals:
        added_msg += f"• {escape_markdown(i)}\n"
    if not (groups or individuals):
        added_msg = "No hay jugadores agregados todavía."

    chat_id = context.user_data.get("chat_id")
    msg_id = context.user_data.get("added_msg_id")

    if not chat_id:
        return

    try:
        if msg_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=added_msg,
                parse_mode="Markdown"
            )
        else:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=added_msg,
                parse_mode="Markdown"
            )
            context.user_data["added_msg_id"] = msg.message_id
    except Exception:
        # Si falla, enviamos uno nuevo
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=added_msg,
            parse_mode="Markdown"
        )
        context.user_data["added_msg_id"] = msg.message_id


# ========================
# Función para enviar mensajes de notificaciones dinámicas
# ========================
async def update_notification(context: ContextTypes.DEFAULT_TYPE, text: str):
    """
    Actualiza siempre el mensaje de notificaciones dinámicas en lugar de crear uno nuevo.
    """
    chat_id = context.user_data.get("chat_id")
    msg_id = context.user_data.get("msg_notify_id")

    if not chat_id or not msg_id:
        return

    text = escape_markdown(text)

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            parse_mode="Markdown"
        )
    except Exception:
        # Si falla editar (mensaje borrado), enviamos uno nuevo
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown"
        )
        context.user_data["msg_notify_id"] = msg.message_id


# ========================
# Actualizar botones top teammates
# ========================
async def update_top_teammates(update_or_query, context: ContextTypes.DEFAULT_TYPE, username: str):
    headers = {"Authorization": f"Bearer {context.user_data.get('token')}"}
    teammates = []
    try:
        resp = requests.get(
            f"{Settings.API_BASE_URL}/player/{username}/top_teammates",
            headers=headers,
            params={"limit": 5},
            timeout=5
        )
        if resp.ok:
            teammates = resp.json()
    except Exception:
        pass

    added_players = set(context.user_data.get("new_match", {}).get("individuals", []))
    top_buttons = []

    # Usuario logueado
    if username not in added_players:
        top_buttons.append(InlineKeyboardButton(f"⭐ {escape_markdown(username)}", callback_data=f"add:individual:{username}"))

    # Top teammates
    for mate in teammates:
        mate_name = mate.get("name")
        if mate_name and mate_name not in added_players and mate_name != username:
            top_buttons.append(InlineKeyboardButton(escape_markdown(mate_name), callback_data=f"add:individual:{mate_name}"))

    chat_id = context.user_data.get("chat_id")
    msg_id = context.user_data.get("msg_top_id")

    if not chat_id:
        return

    try:
        if top_buttons:
            if msg_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text="🟢 Top teammates:",
                    reply_markup=InlineKeyboardMarkup([top_buttons])
                )
            else:
                msg_top = await context.bot.send_message(
                    chat_id=chat_id,
                    text="🟢 Top teammates:",
                    reply_markup=InlineKeyboardMarkup([top_buttons])
                )
                context.user_data["msg_top_id"] = msg_top.message_id
        else:
            if msg_id:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                context.user_data.pop("msg_top_id", None)
    except Exception:
        if top_buttons:
            msg_top = await context.bot.send_message(
                chat_id=chat_id,
                text="🟢 Top teammates:",
                reply_markup=InlineKeyboardMarkup([top_buttons])
            )
            context.user_data["msg_top_id"] = msg_top.message_id
        elif msg_id:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            context.user_data.pop("msg_top_id", None)



# ========================
# Callback principal
# ========================
async def add_player_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split(":")
    action = data_parts[1] if len(data_parts) > 1 else None
    individuals = context.user_data["new_match"]["individuals"]
    username = context.user_data.get("logged_username")

    if action == "individual" and len(data_parts) == 3:
        teammate_username = data_parts[2]
        if teammate_username not in individuals:
            individuals.append(teammate_username)
            await update_notification(context, f"✅ Jugador agregado: {teammate_username}")

        # Actualizamos lista de jugadores
        await update_added_players(query, context)
        # Actualizamos top teammates para ocultar botones de los que ya fueron agregados
        if username:
            await update_top_teammates(query, context, username)
        return MATCH_ADD_PLAYERS

    if action == "group":
        await update_notification(context, "✍️ Escribí los usernames del grupo (separados por espacios o comas): Ej: juan pedro lucas")
        return MATCH_ADD_GROUP

    if action == "individual" and len(data_parts) == 2:
        await update_notification(context, "✍️ Escribí uno o más usernames: Ej: ana martin")
        return MATCH_ADD_INDIVIDUALS

    if action == "done":
        return await finalize_match(query, context)

    if action == "cancel_temp":
        # ✅ Limpiar estado de creación de match
        context.user_data.pop("new_match", None)

        # Borrar todos los mensajes relacionados a la creación de match si existen
        for key in ["msg_info_id", "msg_group_btn_id", "msg_individual_btn_id",
                    "added_msg_id", "msg_notify_id", "msg_top_id", "msg_finish_id"]:
            msg_id = context.user_data.get(key)
            if msg_id:
                try:
                    await context.bot.delete_message(chat_id=context.user_data["chat_id"], message_id=msg_id)
                except Exception:
                    pass  # si ya fue borrado o no existe, ignoramos
                context.user_data.pop(key, None)

        # Volver al menú principal
        await send_post_auth_menu(update, context)

        # Terminar la conversación
        return ConversationHandler.END

    return MATCH_ADD_PLAYERS


# ========================
# Agregar grupo
# ========================
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    text = msg.text.replace(",", " ")
    usernames = [u.strip().lower() for u in text.split() if u]

    if len(usernames) < 2:
        await update_notification(context, "⚠️ Un grupo debe tener al menos 2 jugadores.")
        return MATCH_ADD_PLAYERS

    context.user_data["new_match"]["groups"].append(usernames)
    await update_notification(context, f"✅ Grupo agregado: {', '.join(usernames)}")
    await update_added_players(update, context)

    # 🔥 Borrar mensaje original del usuario
    try:
        await msg.delete()
    except Exception:
        pass  # Si no se puede borrar, ignoramos el error

    return MATCH_ADD_PLAYERS


# ========================
# Agregar jugadores sueltos
# ========================
async def add_individuals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    text = msg.text.replace(",", " ")
    usernames = [u.strip().lower() for u in text.split() if u]

    if not usernames:
        await update_notification(context, "⚠️ No ingresaste usernames válidos.")
        return MATCH_ADD_PLAYERS

    individuals = context.user_data["new_match"]["individuals"]
    added = []
    for u in usernames:
        if u not in individuals:
            individuals.append(u)
            added.append(u)

    if added:
        await update_notification(context, f"✅ Jugadores agregados: {', '.join(added)}")

    await update_added_players(update, context)

    # 🔥 Borrar mensaje original del usuario
    try:
        await msg.delete()
    except Exception:
        pass  # Ignoramos si falla

    return MATCH_ADD_PLAYERS

# ========================
# Finalizar y crear match
# ========================
async def finalize_match(query, context: ContextTypes.DEFAULT_TYPE):
    msg = query.message
    token = context.user_data.get("token")
    data = context.user_data["new_match"]
    team_size = data.get("team_size", 5)

    if not data["groups"] and not data["individuals"]:
        await msg.reply_text("❌ No agregaste jugadores al partido.")
        return MATCH_ADD_PLAYERS

    headers = {"Authorization": f"Bearer {token}"}
    input_groups = data["groups"] + [[u] for u in data["individuals"]]
    if sum(len(group) for group in input_groups) > team_size * 2:
        await msg.reply_text(f"El tamaño elegido admite hasta {team_size * 2} jugadores reales.")
        return MATCH_ADD_PLAYERS

    # ========================
    # Validar todos los players primero
    # ========================
    missing_users = []
    player_objects = []

    for group in input_groups:
        for username in group:
            player_resp = requests.get(
                f"{Settings.API_BASE_URL}/player/{username}",
                headers=headers,
                timeout=5
            )
            if not player_resp.ok:
                missing_users.append(username)
            else:
                player_objects.append(player_resp.json())

    # Si hay usernames que no existen, avisar y volver al menú
    if missing_users:
        valid_usernames = [p["name"] for p in player_objects]

        new_groups = []
        for group in data["groups"]:
            filtered_group = [u for u in group if u in valid_usernames]
            if filtered_group:
                new_groups.append(filtered_group)
        data["groups"] = new_groups

        data["individuals"] = [u for u in data["individuals"] if u in valid_usernames]

        await msg.reply_text(
            f"❌ No se encontraron los siguientes jugadores:\n"
            + ", ".join(missing_users)
            + "\n\n✅ Los jugadores válidos ya se guardaron.\n"
              "Por favor agregá o corregí solo los usernames que faltan."
        )

        #await show_main_menu(query, context, username=context.user_data.get("logged_username"))
        return MATCH_ADD_PLAYERS

    # ========================
    # Crear match si todos los players existen
    # ========================
    match_date = data.get("date")
    match_resp = requests.post(
        f"{Settings.API_BASE_URL}/match/matches",
        headers=headers,
        json={
            "date": match_date.isoformat() if match_date else None,
            "max_players": team_size * 2
        },
        timeout=5
    )

    if not match_resp.ok:
        await msg.reply_text(f"❌ Error al crear el match:\n{match_resp.text}")
        return ConversationHandler.END

    match_id = match_resp.json()["id"]

    for player in player_objects:
        requests.post(
            f"{Settings.API_BASE_URL}/match/matches/{match_id}/players/{player['id']}",
            headers=headers,
            timeout=5
        )

    if data["groups"]:
        requests.post(
            f"{Settings.API_BASE_URL}/match/matches/{match_id}/pre-set-groups",
            headers=headers,
            json={"groups": data["groups"]},
            timeout=5
        )

    await msg.reply_text(
        f"✅ Match creado con ID {match_id}.\n"
        "⚔️ Generando equipos automáticamente..."
    )

    resp = requests.post(
        f"{Settings.API_BASE_URL}/match/matches/{match_id}/generate-teams",
        headers=headers,
        timeout=5
    )

    if resp.ok:
        summary = format_match_summary(resp.json())
        await msg.reply_text(
            "⚔️ Equipos generados automáticamente:\n\n" + summary,
            parse_mode="Markdown"
        )

        try:
            img_resp = requests.post(
                f"{Settings.API_BASE_URL}/match/matches/{match_id}/match-card",
                headers=headers,
                timeout=10
            )

            if img_resp.status_code != 200:
                await msg.reply_text(
                    "⚠️ El match se creó correctamente, pero no se pudo generar la imagen."
                )
            else:
                image_buffer = BytesIO(img_resp.content)
                image_buffer.name = "match_card.png"
                await msg.reply_photo(
                    photo=image_buffer,
                    caption="🖼️ Resumen visual del match"
                )
        except requests.RequestException as e:
            await msg.reply_text(f"⚠️ Error al obtener la imagen del match:\n{e}")

    return ConversationHandler.END

# ========================
# Obtener chat_id seguro
# ========================
def get_chat_id(update_or_query) -> int | None:
    if hasattr(update_or_query, "effective_chat") and update_or_query.effective_chat:
        return update_or_query.effective_chat.id
    if hasattr(update_or_query, "message") and update_or_query.message:
        return update_or_query.message.chat.id
    if hasattr(update_or_query, "callback_query") and update_or_query.callback_query.message:
        return update_or_query.callback_query.message.chat.id
    return None

# ========================
# Utils
# ========================
def escape_markdown(text: str) -> str:
    return (
        text.replace("_", "\\_")
            .replace("*", "\\*")
            .replace("`", "\\`")
    ) if text else ""

def format_match_summary(match: dict) -> str:
    lines = [
        "🎮 *Match creado*",
        "",
        f"🆔 ID: `{match.get('id')}`",
        f"📅 Fecha: {match.get('date')}",
        f"👥 Máx jugadores: {match.get('max_players')}",
        "",
    ]

    def format_team(team: dict, emoji: str):
        if not team:
            return [f"{emoji} Equipo: —"]
        lines = [f"{emoji} *{escape_markdown(team.get('name'))}*"]
        for p in team.get("players", []):
            lines.append(f"   • {escape_markdown(p.get('name'))}")
        return lines

    lines += format_team(match.get("team1"), "🔵")
    lines.append("")
    lines += format_team(match.get("team2"), "🔴")
    return "\n".join(lines)

# ========================
# Cancelar
# ========================
async def cancel_new_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_match", None)
    await update.effective_message.reply_text("❌ Creación de partido cancelada.")
    return ConversationHandler.END
