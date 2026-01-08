import pytest
from fastapi.testclient import TestClient
from typing import Dict
from sqlalchemy.orm import Session
import asyncio

from src.bot.bot_handlers.telegram_match_evaluation import handle_telegram_reply
from src.bot.telegram_sender import TelegramNotificationSender
from src.models import Player, Notification, TelegramIdentity, MatchResultReply
from src.services.telegram_identity_service import link_identity_to_user, create_identity_if_not_exists
from src.test.utils_common_methods import TestUtils

utils = TestUtils()

from datetime import datetime, timedelta, timezone

from src.notification.notification_rules import can_send_notification
from src.models import Match

@pytest.mark.nivel("medio")
def test_balance_creates_match_evaluation_notifications_http(
    client: TestClient,
    db_session: Session
):
    # =====================
    # Crear usuario admin y autenticarse
    # =====================
    admin_id = utils.create_player(
        client,
        "admin_user",
        stats=TestUtils.generate_stats_for_player(100)
    )

    login_res = client.post(
        "/auth/login",
        json={"username": "admin_user", "password": "testpass"}
    )
    assert login_res.status_code == 200

    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # =====================
    # Crear jugadores individuales
    # =====================
    usernames = [f"indiv_{i}" for i in range(6)]
    players: list[Player] = []

    for username in usernames:
        player_id = utils.create_player(client, username)
        player = db_session.query(Player).filter_by(id=player_id).first()
        assert player is not None
        players.append(player)

    # =====================
    # Crear match
    # =====================
    match_data = {
        "date": "2025-07-20T20:00:00",
        "max_players": 6
    }

    res = client.post("/match/matches", json=match_data)
    assert res.status_code == 200

    match = res.json()
    match_id = match["id"]

    # =====================
    # Asignar jugadores al match
    # =====================
    for player in players:
        res = client.post(f"/match/matches/{match_id}/players/{player.id}")
        assert res.status_code == 200

    # =====================
    # Generar equipos (acción bajo test)
    # =====================
    res_balance = client.post(
        f"/match/matches/{match_id}/generate-teams",
        headers=headers
    )
    assert res_balance.status_code == 200

    # =====================
    # Validar notificaciones creadas
    # =====================
    notifications = (
        db_session.query(Notification)
        .filter(Notification.event_type == "MATCH_EVALUATION")
        .all()
    )

    # Solo jugadores con user_id generan notificación
    expected_user_ids = {
        p.user_id for p in players if p.user_id is not None
    }

    assert len(notifications) == len(expected_user_ids)

    notification_user_ids = {n.user_id for n in notifications}
    assert notification_user_ids == expected_user_ids

    for notification in notifications:
        assert notification.channel == "telegram"
        assert notification.status == "pending"
        assert notification.payload["match_id"] == match_id





@pytest.mark.nivel("medio")
def test_match_evaluation_notification_rules(
    client: TestClient,
    db_session: Session
):
    """
    Valida que las reglas de notificación para MATCH_EVALUATION
    se comporten correctamente según la fecha del match.
    """

    # =====================
    # Crear jugador admin y autenticarse
    # =====================
    utils.create_player(
        client,
        "admin_rules_user",
        stats=TestUtils.generate_stats_for_player(100)
    )

    login_res = client.post(
        "/auth/login",
        json={"username": "admin_rules_user", "password": "testpass"}
    )
    assert login_res.status_code == 200

    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # =====================
    # Crear jugadores y obtener Player real vía API
    # =====================
    players: list[Player] = []

    for i in range(2):
        username = f"rules_player_{i}"
        utils.create_player(client, username)

        player_data = utils.get_player(client, username)
        player = db_session.query(Player).filter_by(id=player_data["id"]).first()

        assert player is not None
        assert player.user_id is not None  # sanity check clave

        players.append(player)

    # =====================
    # Crear match en el futuro
    # =====================
    match_date = datetime.now(timezone.utc) + timedelta(hours=2)

    res = client.post(
        "/match/matches",
        json={
            "date": match_date.isoformat(),
            "max_players": 2
        }
    )
    assert res.status_code == 200

    match_id = res.json()["id"]

    # =====================
    # Asignar jugadores y balancear
    # =====================
    for player in players:
        res = client.post(f"/match/matches/{match_id}/players/{player.id}")
        assert res.status_code == 200

    res_balance = client.post(
        f"/match/matches/{match_id}/generate-teams",
        headers=headers
    )
    assert res_balance.status_code == 200

    # =====================
    # Obtener notificación creada
    # =====================
    notification = (
        db_session.query(Notification)
        .filter(Notification.event_type == "MATCH_EVALUATION")
        .order_by(Notification.id.desc())
        .first()
    )

    assert notification is not None
    assert notification.status == "pending"
    assert notification.user is not None

    match = db_session.query(Match).filter_by(id=match_id).first()
    assert match is not None

    # =====================
    # Crear y vincular identidad de Telegram (flujo real)
    # =====================
    identity = create_identity_if_not_exists(
        db_session,
        telegram_user_id=123456789,
        telegram_username="rules_test_user"
    )

    link_identity_to_user(
        db_session,
        identity=identity,
        user=notification.user
    )

    # =====================
    # Caso 1: match NO terminó
    # =====================
    now_before_end = match.date + timedelta(minutes=30)

    assert can_send_notification(
        db_session,
        notification,
        now=now_before_end
    ) is False

    # =====================
    # Caso 2: match terminó (+1h exacta)
    # =====================
    now_exact_end = match.date + timedelta(hours=1)

    assert can_send_notification(
        db_session,
        notification,
        now=now_exact_end
    ) is True

    # =====================
    # Caso 3: match terminó hace más tiempo
    # =====================
    now_after_end = match.date + timedelta(hours=2)

    assert can_send_notification(
        db_session,
        notification,
        now=now_after_end
    ) is True

@pytest.mark.nivel("medio")
def test_telegram_sender_sends_notification(client: TestClient, db_session: Session):

    # =====================
    # Crear jugador vía API y obtener Player real
    # =====================
    username = "sender_user"
    utils.create_player(client, username)
    player_data = utils.get_player(client, username)
    player = db_session.query(Player).filter_by(id=player_data["id"]).first()
    assert player is not None
    assert player.user_id is not None

    # =====================
    # Crear y vincular identidad de Telegram
    # =====================
    identity = create_identity_if_not_exists(
        db_session,
        telegram_user_id=987654321,
        telegram_username="sender_user_telegram"
    )
    link_identity_to_user(db_session, identity, player.user)

    # =====================
    # Crear notificación pendiente
    # =====================
    match_id = 1
    notification = Notification(
        user_id=player.user.id,
        event_type="MATCH_EVALUATION",
        channel="telegram",
        status="pending",
        payload={"match_id": match_id},
        available_at=datetime.utcnow() - timedelta(seconds=1)
    )
    db_session.add(notification)
    db_session.commit()

    # =====================
    # Instanciar sender con mock del app.bot.send_message
    # =====================
    class FakeBot:
        def __init__(self):
            self.sent = []

        async def send_message(self, chat_id, text, **kwargs):
            self.sent.append((chat_id, text))

    class FakeApp:
        def __init__(self):
            self.bot = FakeBot()

    sender = TelegramNotificationSender(FakeApp())

    # =====================
    # Ejecutar envío
    # =====================

    sender.send(notification, db_session)

    # =====================
    # Validar cambios en DB
    # =====================
    db_session.refresh(notification)
    assert notification.status == "sent"
    assert notification.sent_at is not None
    assert len(sender.app.bot.sent) == 1
    chat_id, text = sender.app.bot.sent[0]
    assert chat_id == identity.telegram_user_id
    assert "Puedes evaluar" in text




@pytest.mark.nivel("alto")
def test_telegram_sender_sends_notification(client, db_session):
    # =====================
    # Crear jugador vía API y obtener Player real
    # =====================
    username = "sender_user"
    utils.create_player(client, username)
    player_data = utils.get_player(client, username)
    player = db_session.query(Player).filter_by(id=player_data["id"]).first()
    assert player is not None
    assert player.user_id is not None

    # =====================
    # Crear y vincular identidad de Telegram
    # =====================
    identity = create_identity_if_not_exists(
        db_session,
        telegram_user_id=987654321,
        telegram_username="sender_user_telegram"
    )
    link_identity_to_user(db_session, identity, player.user)

    # =====================
    # Crear notificación pendiente
    # =====================
    match_id = 1
    notification = Notification(
        user_id=player.user.id,
        event_type="MATCH_EVALUATION",
        channel="telegram",
        status="pending",
        payload={"match_id": match_id},
        available_at=datetime.utcnow() - timedelta(seconds=1)
    )
    db_session.add(notification)
    db_session.commit()

    # =====================
    # Instanciar sender con mock del app.bot.send_message
    # =====================
    class FakeBot:
        def __init__(self):
            self.sent = []

        async def send_message(self, chat_id, text, **kwargs):
            self.sent.append((chat_id, text))

    class FakeApp:
        def __init__(self):
            self.bot = FakeBot()

        def create_task(self, coro):
            # Ejecuta la tarea inmediatamente para el test
            asyncio.run(coro)

    sender = TelegramNotificationSender(FakeApp())

    # =====================
    # Ejecutar envío
    # =====================
    sender.send(notification, db_session)

    # =====================
    # Validar cambios en DB
    # =====================
    db_session.refresh(notification)
    assert notification.status == "sent"
    assert notification.sent_at is not None
    assert len(sender.app.bot.sent) == 1

    chat_id, text = sender.app.bot.sent[0]
    assert chat_id == identity.telegram_user_id

    # ✅ Validamos el texto correcto que envía el sender
    assert "El partido terminó. ¿Ganaste o perdiste?" in text


@pytest.mark.nivel("medio")
def test_handle_telegram_reply_registers_response_http(client: TestClient, db_session: Session):

    # =====================
    # Crear jugador vía API
    # =====================
    username = "reply_user"
    utils.create_player(client, username)
    player_data = utils.get_player(client, username)
    player = db_session.query(Player).filter_by(id=player_data["id"]).first()
    assert player is not None
    assert player.user_id is not None

    # =====================
    # Crear y vincular identidad de Telegram
    # =====================
    identity = create_identity_if_not_exists(
        db_session,
        telegram_user_id=111111111,
        telegram_username="reply_user_telegram"
    )
    link_identity_to_user(db_session, identity=identity, user=player.user)

    # =====================
    # Crear un match real
    # =====================
    from src.models import Match
    match = Match(
        date=datetime.utcnow() - timedelta(minutes=5),  # <-- usar "date"
        max_players=2
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    # =====================
    # Simular callback de Telegram
    # =====================
    callback_data = f"match_result:{match.id}:win"

    response = handle_telegram_reply(
        db_session,
        telegram_user_id=111111111,
        callback_data=callback_data
    )

    # =====================
    # Validar respuesta
    # =====================
    assert "✅ Respuesta registrada" in response["text"]

    # =====================
    # Validar que se guardó en DB
    # =====================
    from src.models import MatchResultReply
    reply = db_session.query(MatchResultReply).filter_by(
        user_id=player.user_id,
        match_id=match.id
    ).first()
    assert reply is not None
    assert reply.result == "win"
