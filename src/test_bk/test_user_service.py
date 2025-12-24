# test/test_user_service.py

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pytest
from src.main import app
from src.test.utils_common_methods import TestUtils

utils = TestUtils()
client = TestClient(app)


@pytest.mark.nivel("bajo")
@pytest.mark.usefixtures("db_session")
def test_assign_player_to_match(client, db_session: Session):
    match_id = utils.create_match(client)
    player_id = utils.create_player(client, "player1")

    res = client.post(f"/match/matches/{match_id}/players/{player_id}")
    assert res.status_code == 200
    assert res.json()["message"] == "Jugador asignado exitosamente"


@pytest.mark.nivel("bajo")
def test_exceeding_max_players_should_fail(client, db_session: Session):
    match_id = utils.create_match(client, max_players=2)
    player_ids = [utils.create_player(client, f"extra{i}") for i in range(3)]

    # Asignar dos jugadores correctamente
    for i in range(2):
        res = client.post(f"/match/matches/{match_id}/players/{player_ids[i]}")
        assert res.status_code == 200

    # Tercer jugador debería fallar
    res = client.post(f"/match/matches/{match_id}/players/{player_ids[2]}")
    assert res.status_code == 400
    assert "No se pudo asignar el jugador" in res.json()["detail"]

@pytest.mark.nivel("bajo")
def test_assign_player_to_nonexistent_match_should_fail(client, db_session: Session):
    fake_match_id = 9999
    player_id = utils.create_player(client, "ghost")
    res = client.post(f"/match/matches/{fake_match_id}/players/{player_id}")
    assert res.status_code == 404
    assert "Match o Player no encontrado" in res.json()["detail"]

@pytest.mark.nivel("bajo")
def test_assign_nonexistent_player_should_fail(client, db_session: Session):
    match_id = utils.create_match(client)
    fake_player_id = 9999
    res = client.post(f"/match/matches/{match_id}/players/{fake_player_id}")
    assert res.status_code == 404
    assert "Match o Player no encontrado" in res.json()["detail"]


