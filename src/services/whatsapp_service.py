"""Cliente y lógica mínima para WhatsApp Business Platform Cloud API."""

from typing import Any

import httpx

from src.config import settings
from src.utils.logger_config import app_logger as logger


class WhatsAppService:
    def __init__(self) -> None:
        self.base_url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_GRAPH_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )

    async def send_text(self, recipient: str, text: str) -> None:
        """Envía texto dentro de una conversación iniciada por el usuario."""
        if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
            raise RuntimeError("WhatsApp Cloud API no está configurada")

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": text},
        }
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

        try:
            # El entorno local define proxies inválidos para 127.0.0.1:9.
            # Meta debe contactarse de forma directa, sin heredar esos proxies.
            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("WhatsApp: no se pudo enviar una respuesta: %s", exc)
            raise

    async def handle_webhook(self, payload: dict[str, Any]) -> int:
        """Procesa mensajes de texto entrantes y devuelve cuántos fueron atendidos."""
        processed = 0
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    if message.get("type") != "text":
                        continue

                    sender = message.get("from")
                    text = message.get("text", {}).get("body", "").strip()
                    if not sender:
                        continue

                    try:
                        await self.send_text(sender, self._reply_for(text))
                        processed += 1
                    except httpx.HTTPError:
                        # Respondemos 200 a Meta para no duplicar el webhook.
                        # El detalle técnico ya quedó registrado en app.log.
                        continue

        if processed:
            logger.info("WhatsApp: %s mensaje(s) entrante(s) procesado(s)", processed)
        return processed

    @staticmethod
    def _reply_for(text: str) -> str:
        command = text.casefold().strip()
        if command in {"hola", "inicio", "start"}:
            return "Bienvenido a Max_io. Escribí AYUDA para ver las opciones disponibles."
        if command in {"ayuda", "help"}:
            return "Max_io\n\n- HOLA: volver al inicio\n- AYUDA: ver opciones\n\nPróximamente vas a poder consultar jugadores y armar partidos desde acá."
        return "No entendí ese mensaje. Escribí AYUDA para ver las opciones disponibles."
