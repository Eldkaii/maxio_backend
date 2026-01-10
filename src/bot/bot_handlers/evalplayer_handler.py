from telegram.ext import ContextTypes, ConversationHandler
from telegram import Update
import requests
from src.config import Settings


from src.bot.commands.evalplayer import SELECT_BUTTONS, generar_texto_stat, fila_labels, VALOR_MAP
from src.database import get_db
from src.services.telegram_identity_service import get_identity_by_telegram_user_id, is_identity_linked


async def evalplayer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    username, fila_idx, col = data[1], int(data[2]), int(data[3])

    eval_data = context.user_data.get("evalplayer")
    if not eval_data:
        await query.message.reply_text("Error: conversación no iniciada.")
        return ConversationHandler.END

    # Guardamos selección
    eval_data["selecciones"][fila_idx] = col

    # Actualizar el mensaje correspondiente
    msg_id = eval_data["messages"].get(fila_idx)
    if msg_id:
        texto_actualizado = generar_texto_stat(username, eval_data["stats"], fila_idx, eval_data["selecciones"])
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=msg_id,
            text=texto_actualizado,
            reply_markup=None
        )

    # Si ya se completaron las 5 selecciones
    if len(eval_data["selecciones"]) == 5:
        # Calculamos stats finales
        stats_reales = eval_data["stats"]
        stats_payload = {}
        for fila_idx, boton in eval_data["selecciones"].items():
            stat = fila_labels[fila_idx].lower()
            valor_base = stats_reales[stat]
            valor_final = valor_base + VALOR_MAP[boton]
            valor_final = max(0, min(100, valor_final))  # limitar entre 0 y 100
            stats_payload[stat] = round(valor_final, 2)

        # Obtener evaluator_username desde Telegram Identity
        db = next(get_db())
        identity = get_identity_by_telegram_user_id(
            db=db,
            telegram_user_id=update.effective_user.id
        )
        if not identity or not is_identity_linked(identity):
            await query.message.reply_text(
                "❌ No estás logueado. Usá /start para iniciar sesión."
            )
            return ConversationHandler.END

        evaluator_username = identity.user.username
        context.user_data["logged_username"] = evaluator_username  # guardamos para futuras referencias

        # Enviar al backend
        try:
            params = {"evaluator_username": evaluator_username}  # va en query
            response = requests.put(
                f"{Settings.API_BASE_URL}/player/{username}/stats",  # CORRECTO: /player/
                params=params,
                json=stats_payload,
                timeout=5
            )
            response.raise_for_status()
            await query.message.reply_text(
                f"✅ Evaluación enviada correctamente al backend.\nJugador: {username}"
            )
        except requests.RequestException as e:
            await query.message.reply_text(f"❌ Error al enviar stats: {str(e)}")

        # Limpiar contexto
        context.user_data.pop("evalplayer", None)

    return SELECT_BUTTONS
