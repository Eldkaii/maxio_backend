import pytest
from fastapi.testclient import TestClient
from typing import Dict
from sqlalchemy.orm import Session

from src.models import Player, Notification, TelegramIdentity
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
        "fecha": "2025-07-20T20:00:00",
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
            "fecha": match_date.isoformat(),
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
