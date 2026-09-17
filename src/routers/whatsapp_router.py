"""Webhook de entrada para WhatsApp Business Platform Cloud API."""

import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from src.config import settings
from src.services.whatsapp_service import WhatsAppService
from src.utils.logger_config import app_logger as logger

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])
whatsapp_service = WhatsAppService()


@router.get("")
async def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """Responde el desafío que Meta envía al registrar el webhook."""
    if (
        hub_mode != "subscribe"
        or not hub_challenge
        or not settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        or not hmac.compare_digest(
            hub_verify_token or "", settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        )
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Webhook no autorizado")
    return Response(content=hub_challenge, media_type="text/plain")


@router.post("", status_code=status.HTTP_200_OK)
async def receive_webhook(request: Request):
    """Valida y procesa notificaciones entrantes de Meta."""
    raw_body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")
    expected_signature = "sha256=" + hmac.new(
        (settings.META_APP_SECRET or "").encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not settings.META_APP_SECRET or not hmac.compare_digest(signature, expected_signature):
        logger.warning("Webhook de WhatsApp rechazado: firma inválida")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Firma inválida")

    payload = await request.json()
    await whatsapp_service.handle_webhook(payload)
    return {"status": "ok"}
