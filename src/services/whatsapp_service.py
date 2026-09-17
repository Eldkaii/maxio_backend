"""Cliente y punto de entrada para WhatsApp Business Platform Cloud API."""

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
        await self._send_message(recipient, {
            "messaging_product": "whatsapp", "to": recipient, "type": "text", "text": {"body": text},
        })

    async def send_buttons(self, recipient: str, text: str, buttons: list[tuple[str, str]]) -> None:
        if not 1 <= len(buttons) <= 3:
            raise ValueError("WhatsApp admite entre uno y tres botones de respuesta")
        if any(len(title) > 20 for _, title in buttons):
            raise ValueError("El título de un botón de WhatsApp admite como máximo 20 caracteres")
        await self._send_message(recipient, {
            "messaging_product": "whatsapp", "to": recipient, "type": "interactive",
            "interactive": {
                "type": "button", "body": {"text": text},
                "action": {"buttons": [
                    {"type": "reply", "reply": {"id": action_id, "title": title}}
                    for action_id, title in buttons
                ]},
            },
        })

    async def send_image(self, recipient: str, image: bytes, caption: str, filename: str) -> None:
        self._ensure_configured()
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
        media_url = f"https://graph.facebook.com/{settings.WHATSAPP_GRAPH_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/media"
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.post(
                media_url, headers=headers, data={"messaging_product": "whatsapp"},
                files={"file": (filename, image, "image/png")},
            )
            response.raise_for_status()
        await self._send_message(recipient, {
            "messaging_product": "whatsapp", "to": recipient, "type": "image",
            "image": {"id": response.json()["id"], "caption": caption},
        })

    async def send_list(
        self,
        recipient: str,
        text: str,
        button_label: str,
        rows: list[tuple[str, str, str | None]],
    ) -> None:
        """Envía una lista interactiva de WhatsApp de hasta diez opciones."""
        if not 1 <= len(rows) <= 10:
            raise ValueError("WhatsApp admite entre una y diez opciones por lista")
        await self._send_message(recipient, {
            "messaging_product": "whatsapp", "to": recipient, "type": "interactive",
            "interactive": {
                "type": "list", "body": {"text": text},
                "action": {
                    "button": button_label,
                    "sections": [{"title": "Opciones", "rows": [
                        {"id": row_id, "title": title, **({"description": description} if description else {})}
                        for row_id, title, description in rows
                    ]}],
                },
            },
        })

    async def download_media(self, media_id: str) -> tuple[bytes, str]:
        self._ensure_configured()
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
        metadata_url = f"https://graph.facebook.com/{settings.WHATSAPP_GRAPH_API_VERSION}/{media_id}"
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            metadata = await client.get(metadata_url, headers=headers)
            metadata.raise_for_status()
            media = await client.get(metadata.json()["url"], headers=headers)
            media.raise_for_status()
        return media.content, metadata.json().get("mime_type", "application/octet-stream")

    def _ensure_configured(self) -> None:
        if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
            raise RuntimeError("WhatsApp Cloud API no está configurada")

    async def _send_message(self, recipient: str, payload: dict[str, Any]) -> None:
        self._ensure_configured()
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
        try:
            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("WhatsApp: no se pudo enviar una respuesta: %s", exc)
            raise

    async def handle_webhook(self, payload: dict[str, Any]) -> int:
        """Procesa mensajes entrantes y delega los flujos a la capa conversacional."""
        from src.services.whatsapp_conversation_service import WhatsAppConversationService

        processed = 0
        conversation = WhatsAppConversationService(self)
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = {
                    contact.get("wa_id"): contact.get("profile", {}).get("name")
                    for contact in value.get("contacts", [])
                }
                for message in value.get("messages", []):
                    sender = message.get("from")
                    if not sender:
                        continue
                    try:
                        await conversation.process(
                            wa_id=sender, profile_name=contacts.get(sender),
                            message_id=message.get("id"), message_type=message.get("type", ""),
                            text=self._incoming_text(message), media=message.get("image"),
                        )
                        processed += 1
                    except Exception:
                        logger.exception("WhatsApp: no se pudo procesar un mensaje entrante")

        if processed:
            logger.info("WhatsApp: %s mensaje(s) entrante(s) procesado(s)", processed)
        return processed

    @staticmethod
    def _incoming_text(message: dict[str, Any]) -> str:
        if message.get("type") == "text":
            return message.get("text", {}).get("body", "").strip()
        if message.get("type") == "interactive":
            interactive = message.get("interactive", {})
            reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
            return reply.get("id", "")
        return ""

    @staticmethod
    def _reply_for(text: str) -> str:
        """Compatibilidad con la respuesta básica de la primera conexión."""
        if text.casefold().strip() in {"hola", "inicio", "start"}:
            return "Bienvenido a Max_io. Escribí INICIO para ver las opciones disponibles."
        return "Escribí INICIO para ver las opciones disponibles."
