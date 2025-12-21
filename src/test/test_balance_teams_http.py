import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.models import Player
from src.test.test_full_flow_2 import generate_stats_for_player
from src.utils.logger_config import test_logger as logger
from src.test.utils_common_methods import TestUtils

utils = TestUtils()

@pytest.mark.nivel("medio")
def test_balance_individual_players_http(client: TestClient, db_session: Session):
    # Crear un usuario que vamos a usar para autenticarnos
    admin_id = utils.create_player(client, "admin_user", stats=generate_stats_for_player(100))
    login_res = client.post("/auth/login", json={"username": "admin_user", "password": "testpass"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Crear 6 jugadores individuales usando TestUtils.create_player()
    usernames = [f"indiv_{i}" for i in range(6)]
    players = []

    for username in usernames:
        player_id = utils.create_player(client, username)
        player = db_session.query(Player).filter_by(id=player_id).first()
        assert player is not None
        players.append(player)

    # 2. Crear un Match vía endpoint
    match_data = {
        "fecha": "2025-07-20T20:00:00",
        "max_players": 6
    }
    res = client.post("/match/matches", json=match_data)
    assert res.status_code == 200
    match = res.json()
    match_id = match["id"]

    # 3. Asignar jugadores al match sin equipo aún
    for player in players:
        res = client.post(f"/match/matches/{match_id}/players/{player.id}")
        assert res.status_code == 200

    # 4. Generar los equipos vía endpoint de balanceo
    res_balance = client.post(f"/match/matches/{match_id}/generate-teams", headers=headers)
    assert res_balance.status_code == 200
    data = res_balance.json()

    team1_ids = [p["id"] for p in data.get("team1", {}).get("players", [])]
    team2_ids = [p["id"] for p in data.get("team2", {}).get("players", [])]

    assert len(team1_ids) == len(team2_ids) == 3
    assert set(team1_ids).isdisjoint(team2_ids)


