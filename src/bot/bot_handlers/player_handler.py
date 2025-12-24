
from io import BytesIO

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from src.database import get_db
from src.config import settings
from src.services.telegram_identity_service import (
    get_identity_by_telegram_user_id,
    is_identity_linked,
)


async def handle_profile_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Solo procesar si el bot espera una foto
    if not context.user_data.get("awaiting_photo"):
        return

    # Validar que realmente sea una foto
    if not update.message or not update.message.photo:
        await update.message.reply_text("❌ Eso no es una foto.")
        return

    db = next(get_db())

    # 🔑 Obtener identidad desde DB usando telegram_user_id
    identity = get_identity_by_telegram_user_id(
        db=db,
        telegram_user_id=update.effective_user.id
    )

    if not identity or not is_identity_linked(identity):
        await update.message.reply_text(
            "❌ Tu sesión expiró. Usá /start para iniciar sesión nuevamente."
        )
        context.user_data.pop("awaiting_photo", None)
        return

    # ✅ Username desde la relación ORM
    username = identity.user.username

    # 📸 Foto en máxima calidad
    photo = update.message.photo[-1]
    telegram_file = await photo.get_file()

    buffer = BytesIO()
    await telegram_file.download_to_memory(out=buffer)
    buffer.seek(0)

    # 🌐 Enviar a la API
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{settings.API_BASE_URL}/player/{username}/photo",
            files={
                "file": ("profile.jpg", buffer, "image/jpeg")
            },
            timeout=30
        )

    # 🧹 Limpiar estado conversacional
    context.user_data.pop("awaiting_photo", None)

    # 📢 Feedback al usuario
    if res.status_code == 200:
        await update.message.reply_text("✅ Foto de perfil actualizada.")

    else:
        try:
            detail = res.json().get("detail", "Error desconocido")
        except Exception:
            detail = "Error desconocido"

        await update.message.reply_text(
            f"❌ Error al subir la foto:\n{detail}"
        )

