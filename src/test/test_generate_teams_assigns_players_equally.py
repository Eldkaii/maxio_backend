import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.test.utils_common_methods import TestUtils
from src.utils.logger_config import test_logger as logger

utils = TestUtils()


@pytest.mark.nivel("bajo")
def test_generate_teams_assigns_players_equally(client: TestClient, db_session: Session):

    # Crear un usuario que vamos a usar para autenticarnos
    admin_id = utils.create_player(client, "admin_user")
    login_res = client.post("/auth/login", json={"username": "admin_user", "password": "testpass"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}


    logger.info("Creando un nuevo match con máximo 6 jugadores")
    match_id = utils.create_match(client, max_players=6)

    logger.info("Creando y asignando 6 jugadores al match")
    player_ids = []
    for i in range(6):
        username = f"PINuser{i}"
        player_id = utils.create_player(client, username)
        player_ids.append(player_id)
        utils.assign_player_to_match(client, match_id, player_id)

    logger.info("Generando equipos automáticamente para el match")
    res = client.post(f"/match/matches/{match_id}/generate-teams", headers=headers)
    assert res.status_code == 200, f"Error al generar equipos: {res.text}"
    data = res.json()

    assert data["team1"] is not None
    assert data["team2"] is not None

    team1_players = data["team1"].get("players", [])
    team2_players = data["team2"].get("players", [])

    logger.info(f"Jugadores asignados - team1: {len(team1_players)}, team2: {len(team2_players)}")

    assert len(team1_players) + len(team2_players) == 6, "No se asignaron los 6 jugadores"

    # Verificar duplicados en cada equipo
    team1_ids = [p["id"] for p in team1_players]
    team2_ids = [p["id"] for p in team2_players]

    assert len(team1_ids) == len(set(team1_ids)), "Hay jugadores duplicados en team1"
    assert len(team2_ids) == len(set(team2_ids)), "Hay jugadores duplicados en team2"

    interseccion = set(team1_ids).intersection(set(team2_ids))
    assert len(interseccion) == 0, f"Jugadores duplicados entre ambos equipos: {interseccion}"

    # Verificar que el balanceo sea razonable
    diferencia = abs(len(team1_ids) - len(team2_ids))
    assert diferencia <= 1, f"Equipos desbalanceados: diferencia de {diferencia} jugadores"
