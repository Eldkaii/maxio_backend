# src/test/test_assign_player_http.py

import pytest
from fastapi import status
from sqlalchemy.orm import Session
from src.test.utils_common_methods import TestUtils

utils = TestUtils()

@pytest.mark.nivel("bajo")
@pytest.mark.usefixtures("client", "db_session")
def test_assign_players_successfully(client, db_session: Session):
    match_id = utils.create_match(client)
    player_ids = utils.create_players(client, ["pp_A", "pp_B"])

    utils.assign_players_to_match(client, match_id, player_ids)

@pytest.mark.nivel("bajo")
@pytest.mark.usefixtures("client", "db_session")
def test_duplicate_player_in_match_should_fail(client, db_session: Session):
    match_id = utils.create_match(client)
    player_id = utils.create_player(client, "pp_dup")

    # Primera asignación (exitosa)
    utils.assign_player_to_match(client, match_id, player_id)

    # Segunda asignación (debe fallar)
    res = client.post(f"/match/matches/{match_id}/players/{player_id}")
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "No se pudo asignar el jugador" in res.json()["detail"]


@pytest.mark.nivel("bajo")
@pytest.mark.usefixtures("client", "db_session")
def test_exceeding_max_players_should_fail(client, db_session: Session):
    match_id = utils.create_match(client, max_players=2)
    player_ids = utils.create_players(client, ["pp1", "pp2", "pp3"])

    # Asignar dos primeros (ok)
    utils.assign_players_to_match(client, match_id, player_ids[:2])

    # Asignar tercero (debe fallar)
    res = client.post(f"/match/matches/{match_id}/players/{player_ids[2]}")
    assert res.status_code == status.HTTP_400_BAD_REQUEST
