import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.main import app
from src.models import Player
from src.test.utils_common_methods import TestUtils

client = TestClient(app)


# @pytest.fixture(scope="function")
# def db_session():
#     from src.database import SessionLocal
#     session = SessionLocal()
#     try:
#         yield session
#     finally:
#         session.close()

@pytest.mark.nivel("medio")
def test_full_match_flow(client: TestClient, db_session: Session):
    utils = TestUtils()
    # 1. Crear 6 users con players usando método común
    usernames = [f"user{i}" for i in range(6)]
    player_ids = utils.create_players(client, usernames)

    # Obtener instancias Player de la DB para luego asignar team
    players = [db_session.query(Player).get(pid) for pid in player_ids]
    assert all(players), "Error: alguno de los players no existe en la DB"

    # 2. Crear un Match
    match_id = utils.create_match(client, max_players=6)

    # 3. Asignar jugadores al match usando endpoint (reemplaza asociación directa)
    # Asumimos que el endpoint sólo asigna al match, equipo se asigna luego
    for pid in player_ids:
        utils.assign_player_to_match(client, match_id, pid)

    # 4. Crear 2 teams con los jugadores (usando método común)
    team_a_id = utils.create_team(db_session, player_ids[:3], name="Team A")
    team_b_id = utils.create_team(db_session, player_ids[3:], name="Team B")

    # 5. Asignar teams al match usando endpoint (método común)
    utils.assign_team_to_match(client, team_a_id, match_id)
    utils.assign_team_to_match(client, team_b_id, match_id)

    # Validaciones simples
    # Verificamos que los teams existen en DB y tienen los jugadores
    team_a = db_session.query(Player).join(Player.teams).filter_by(id=team_a_id).first()
    team_b = db_session.query(Player).join(Player.teams).filter_by(id=team_b_id).first()
    assert team_a is not None
    assert team_b is not None

    print("✅ Test de integración completo exitoso 🎉")
