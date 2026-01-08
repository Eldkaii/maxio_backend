from sqlalchemy.orm import Session
from src.models import MatchResultReply
from src.services.telegram_identity_service import get_identity_by_telegram_user_id

def handle_telegram_reply(
    db: Session,
    telegram_user_id: int,
    callback_data: str,
) -> dict:
    """
    Maneja la respuesta de un usuario vía Telegram sobre si ganó o perdió un match.
    Solo registra la respuesta y devuelve un mensaje de guía para evaluar jugadores.
    """

    print("callback_data:", callback_data, "telegram_user_id:", telegram_user_id)

    # 1️⃣ Obtener identidad activa por telegram_user_id
    identity = get_identity_by_telegram_user_id(db, telegram_user_id)
    if not identity or not identity.user_id:
        return {"text": "❌ Tu cuenta de Telegram no está vinculada a un usuario."}

    # 2️⃣ Validar formato de callback_data
    if not callback_data.startswith("match_result:"):
        return {"text": "Comando no reconocido."}

    # Formato esperado: match_result:<match_id>:win|lose
    try:
        _, match_id_str, result = callback_data.split(":")
        match_id = int(match_id_str)
        result = result.lower()
    except Exception:
        return {"text": "Comando inválido o mal formado."}

    # 3️⃣ Revisar si ya respondió
    already_replied = db.query(MatchResultReply).filter_by(
        match_id=match_id,
        user_id=identity.user_id,
    ).first()

    if already_replied:
        return {"text": "ℹ️ Ya registramos tu respuesta para este partido."}

    # 4️⃣ Guardar respuesta
    reply = MatchResultReply(
        match_id=match_id,
        user_id=identity.user_id,
        result=result,
    )
    db.add(reply)
    db.commit()

    # 5️⃣ Mensaje final al usuario
    return {
        "text": (
            "✅ Respuesta registrada.\n\n"
            "Puedes evaluar el rendimiento de los demás jugadores "
            "usando el comando:\n"
            "/eval_player USERNAME"
        )
    }
