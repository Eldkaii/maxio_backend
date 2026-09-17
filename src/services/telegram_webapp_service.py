import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import HTTPException, status

from src.config import settings


def validate_init_data(init_data: str) -> dict:
    """Valida la firma oficial de Telegram Web App y devuelve sus datos."""
    if not init_data or not settings.TELEGRAM_TOKEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Datos de Telegram ausentes")

    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma de Telegram ausente")

    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", settings.TELEGRAM_TOKEN.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma de Telegram inválida")

    auth_date = values.get("auth_date")
    if auth_date:
        try:
            if time.time() - int(auth_date) > 86400:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Datos de Telegram expirados")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Fecha de Telegram inválida")

    try:
        telegram_user = json.loads(values.get("user", "{}"))
        telegram_user["id"] = int(telegram_user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario de Telegram inválido")
    return telegram_user
