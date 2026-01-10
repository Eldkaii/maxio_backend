from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler
import requests
from src.config import Settings

SELECT_BUTTONS = 0

# ========================
# Configuración
# ========================

fila_labels = ["AURA", "TIRO", "RITMO", "FISICO", "DEFENSA"]

EMOJIS_POR_STAT = {
    "aura":   ["💀🔻", "🔻", "⚪", "🔺", "🔺🔥"],
    "tiro":   ["💀🔻", "🔻", "⚪", "🔺", "🔺🔥"],
    "ritmo":  ["💀🔻", "🔻", "⚪", "🔺", "🔺🔥"],
    "fisico": ["💀🔻", "🔻", "⚪", "🔺", "🔺🔥"],
    "defensa":["💀🔻", "🔻", "⚪", "🔺", "🔺🔥"]
}

ICONOS_POR_STAT = {
    "aura": "✨",
    "tiro": "🎯",
    "ritmo": "⚡",
    "fisico": "💪",
    "defensa": "🛡️"
}

# Impacto de cada botón
VALOR_MAP = {0: -15, 1: -7, 2: 0, 3: 7, 4: 15}


# ========================
# Funciones auxiliares
# ========================

def generar_botones_stat(username: str, fila_idx: int) -> InlineKeyboardMarkup:
    stat = fila_labels[fila_idx].lower()
    emojis = EMOJIS_POR_STAT.get(stat, ["🔻🔻", "🔻", "⚪", "🔺", "🔺🔺"])
    row_buttons = [
        InlineKeyboardButton(emoji, callback_data=f"eval:{username}:{fila_idx}:{col}")
        for col, emoji in enumerate(emojis)
    ]
    return InlineKeyboardMarkup([row_buttons])


def generar_texto_stat(username: str, stats: dict, fila_idx: int, selecciones: dict) -> str:
    label = fila_labels[fila_idx]
    valor_actual = stats[label.lower()]
    sel = selecciones.get(fila_idx)

    icono = ICONOS_POR_STAT.get(label.lower(), "💫")
    emojis = EMOJIS_POR_STAT.get(label.lower(), ["💀🔻", "🔻", "⚪", "🔺", "🔺🔥"])
    sel_text = emojis[sel] if sel is not None else "❌"

    separador = "━━━━━━━━━━━━━━━━━━━━━━━\n━━━━━━━━━━━━━━━━━━━━━━━"

    return f"{separador}\n{icono} {label}: {valor_actual:.1f}\nTu evaluación: {sel_text}"


# ========================
# Comando /evalplayer
# ========================

async def evalplayer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Debes indicar un username. Ejemplo: /evalplayer Alice")
        return ConversationHandler.END

    username = context.args[0]

    # Llamada al backend para obtener stats
    try:
        response = requests.get(f"{Settings.API_BASE_URL}/player/{username}", timeout=5)
        response.raise_for_status()
        player_data = response.json()
    except requests.RequestException:
        await update.message.reply_text(f"No se pudo obtener información del jugador '{username}'")
        return ConversationHandler.END

    # Guardamos stats y selecciones vacías
    context.user_data["evalplayer"] = {
        "username": username,
        "selecciones": {},  # {fila_idx: valor_seleccionado}
        "stats": {
            "aura": player_data["aura"],
            "tiro": player_data["tiro"],
            "ritmo": player_data["ritmo"],
            "fisico": player_data["fisico"],
            "defensa": player_data["defensa"],
        },
        "messages": {},  # {fila_idx: message_id} para actualizar luego
    }

    eval_data = context.user_data["evalplayer"]

    # Enviar los 5 mensajes simultáneamente
    for fila_idx in range(5):
        texto = generar_texto_stat(username, eval_data["stats"], fila_idx, eval_data["selecciones"])
        reply_markup = generar_botones_stat(username, fila_idx)
        msg = await update.message.reply_text(text=texto, reply_markup=reply_markup)
        eval_data["messages"][fila_idx] = msg.message_id

    return SELECT_BUTTONS


