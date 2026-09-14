"""Pruebas aisladas de la conexión y el enrutamiento de WhatsApp Cloud API.

No llaman a Meta ni envían mensajes a números reales.
"""

import asyncio
import hashlib
import hmac
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.routers import whatsapp_router
from src.services.whatsapp_conversation_service import WhatsAppConversationService
from src.services.whatsapp_service import WhatsAppService


@pytest.mark.nivel("bajo")
def test_whatsapp_webhook_verification_accepts_valid_challenge(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "test-token")
    response = client.get("/webhooks/whatsapp", params={
        "hub.mode": "subscribe", "hub.verify_token": "test-token", "hub.challenge": "challenge-123",
    })
    assert response.status_code == 200
    assert response.text == "challenge-123"


@pytest.mark.nivel("bajo")
def test_whatsapp_webhook_rejects_invalid_signature(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "META_APP_SECRET", "test-app-secret")
    response = client.post(
        "/webhooks/whatsapp", content=b'{"object":"whatsapp_business_account"}',
        headers={"x-hub-signature-256": "sha256=invalid"},
    )
    assert response.status_code == 403


@pytest.mark.nivel("bajo")
def test_whatsapp_webhook_accepts_signed_message(client: TestClient, monkeypatch):
    secret = "test-app-secret"
    payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {"messages": []}}]}]}
    raw_body = b'{"object":"whatsapp_business_account","entry":[{"changes":[{"value":{"messages":[]}}]}]}'
    signature = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    handle_webhook = AsyncMock(return_value=0)
    monkeypatch.setattr(settings, "META_APP_SECRET", secret)
    monkeypatch.setattr(whatsapp_router.whatsapp_service, "handle_webhook", handle_webhook)
    response = client.post("/webhooks/whatsapp", content=raw_body, headers={
        "content-type": "application/json", "x-hub-signature-256": signature,
    })
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    handle_webhook.assert_awaited_once_with(payload)


@pytest.mark.nivel("bajo")
def test_whatsapp_service_delegates_text_to_persistent_conversation(monkeypatch):
    service = WhatsAppService()
    process = AsyncMock()
    monkeypatch.setattr(WhatsAppConversationService, "process", process)
    payload = {"entry": [{"changes": [{"value": {"contacts": [{"wa_id": "59800000000", "profile": {"name": "Test"}}], "messages": [{
        "type": "text", "from": "59800000000", "id": "wamid-test-1", "text": {"body": "Hola"},
    }]}}]}]}

    assert asyncio.run(service.handle_webhook(payload)) == 1
    process.assert_awaited_once_with(
        wa_id="59800000000", profile_name="Test", message_id="wamid-test-1",
        message_type="text", text="Hola", media=None,
    )


@pytest.mark.nivel("bajo")
def test_whatsapp_match_datetime_accepts_expected_format():
    result = WhatsAppConversationService._parse_match_datetime("25/12/2026 20:30")

    assert result is not None
    assert result.isoformat() == "2026-12-25T20:30:00"


@pytest.mark.nivel("bajo")
def test_whatsapp_match_datetime_rejects_invalid_format():
    assert WhatsAppConversationService._parse_match_datetime("2026-12-25 20:30") is None


@pytest.mark.nivel("bajo")
def test_whatsapp_service_reads_interactive_button_id():
    message = {"type": "interactive", "interactive": {"type": "button_reply", "button_reply": {"id": "menu_profile"}}}
    assert WhatsAppService._incoming_text(message) == "menu_profile"


@pytest.mark.nivel("bajo")
def test_whatsapp_service_sends_interactive_list(monkeypatch):
    service = WhatsAppService()
    send_message = AsyncMock()
    monkeypatch.setattr(service, "_send_message", send_message)

    asyncio.run(service.send_list(
        "59800000000", "Evaluá tiro", "Puntuar",
        [("eval_score_0", "Muy bajo", "-15 puntos"), ("eval_score_4", "Excelente", "+15 puntos")],
    ))

    payload = send_message.await_args.args[1]
    assert payload["interactive"]["type"] == "list"
    assert payload["interactive"]["action"]["sections"][0]["rows"][1]["id"] == "eval_score_4"


@pytest.mark.nivel("bajo")
def test_whatsapp_service_rejects_button_title_longer_than_twenty_characters():
    service = WhatsAppService()

    with pytest.raises(ValueError, match="máximo 20"):
        asyncio.run(service.send_buttons("59800000000", "Menú", [("action", "Evaluar último partido")]))


@pytest.mark.nivel("bajo")
def test_whatsapp_evaluation_scores_accepts_five_ratings():
    assert WhatsAppConversationService._parse_evaluation_scores("3, 4, 2, 5, 4") == [3, 4, 2, 5, 4]


@pytest.mark.nivel("bajo")
def test_whatsapp_evaluation_scores_rejects_invalid_ratings():
    assert WhatsAppConversationService._parse_evaluation_scores("3,4,5") is None
    assert WhatsAppConversationService._parse_evaluation_scores("3,4,2,5,6") is None


@pytest.mark.nivel("bajo")
def test_whatsapp_normalizes_usernames_to_lowercase():
    names, groups = WhatsAppConversationService._parse_match_players("ANA,[Juan,PEDRO]")

    assert names == ["ana", "juan", "pedro"]
    assert groups == [["juan", "pedro"]]
