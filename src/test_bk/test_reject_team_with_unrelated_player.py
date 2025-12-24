import pytest
from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.testclient import TestClient
from src.main import app

from src.models import Team, Player
from src.utils.logger_config import test_logger as logger
from src.test.utils_common_methods import TestUtils

utils = TestUtils()
client = TestClient(app)

@pytest.mark.nivel("medio")
def create_match(client, max_players=4):
    res = client.post("/match/matches", json={"fecha": "2025-07-19T10:00:00", "max_players": max_players})
    assert res.status_code == status.HTTP_200_OK
    return res.json()

@pytest.mark.nivel("medio")
def create_team(db_session: Session, players, name="EquipoTest"):
    team = Team(name=name, players=players)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team

@pytest.mark.nivel("medio")
def test_team_size_exceeds_half_max(client: TestClient, db_session: Session):
    match_id = utils.create_match(client, max_players=4)

    # Crear jugadores usando TestUtils
    # Crear jugadores usando TestUtils
    player_ids = [utils.create_player(client, f"user{i}") for i in range(3)]
    players = db_session.query(Player).filter(Player.id.in_(player_ids)).all()

    # Crear equipo con esos jugadores (usando db_session directamente o método común si existe)
    # Suponiendo que no hay método común para crear equipo, hacemos manual:
    from src.models import Team
    team = Team(name="EquipoTest", players=players)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    res = client.post(f"/match/matches/{match_id}/teams/{team.id}")
    assert res.status_code >= 400

@pytest.mark.nivel("medio")
def test_team_already_assigned(client, db_session: Session):
    match_id = utils.create_match(client, max_players=4)
    players = [utils.create_player(client,"player1"), utils.create_player(client,"player2")]
    player_objs = [db_session.query(Player).filter(Player.id == pid).first() for pid in players]
    team = create_team(db_session, player_objs)

    res1 = client.post(f"/match/matches/{match_id}/teams/{team.id}")
    assert res1.status_code == 200

    res2 = client.post(f"/match/matches/{match_id}/teams/{team.id}")
    assert res2.status_code >= 400

@pytest.mark.nivel("medio")
def test_players_overlap_with_other_team(client, db_session: Session):
    match_id = utils.create_match(client, max_players=4)

    p1 = utils.create_player(client,"USERp1")
    p2 = utils.create_player(client,"USERp2")
    p3 = utils.create_player(client,"USERp3")

    p1_obj = db_session.query(Player).filter(Player.id == p1).first()
    p2_obj = db_session.query(Player).filter(Player.id == p2).first()
    p3_obj = db_session.query(Player).filter(Player.id == p3).first()

    team1 = create_team(db_session, [p1_obj, p2_obj])
    team2 = create_team(db_session, [p2_obj, p3_obj])  # p2 repite

    res1 = client.post(f"/match/matches/{match_id}/teams/{team1.id}")
    assert res1.status_code == 200

    res2 = client.post(f"/match/matches/{match_id}/teams/{team2.id}")
    assert res2.status_code >= 400

@pytest.mark.nivel("medio")
def test_players_exceed_match_max(client, db_session: Session):
    match = create_match(client, max_players=4)

    # Insertamos 3 jugadores al match manualmente (usando db)
    existing_players = [utils.create_player(client,f"NOTex{i}") for i in range(3)]
    existing_player_objs = [db_session.query(Player).filter(Player.id == pid).first() for pid in existing_players]

    for p in existing_player_objs:
        db_session.execute(
            text("INSERT INTO match_players (match_id, player_id, team) VALUES (:match_id, :player_id, :team)"),
            {"match_id": match['id'], "player_id": p.id, "team": "team1"}
        )
    db_session.commit()

    # Crear un equipo con 2 jugadores (3 + 2 > 4)
    new_players = [utils.create_player(client,f"np{i}") for i in range(2)]
    new_player_objs = [db_session.query(Player).filter(Player.id == pid).first() for pid in new_players]

    team = create_team(db_session, new_player_objs)

    res = client.post(f"/match/matches/{match['id']}/teams/{team.id}")
    assert res.status_code >= 400

@pytest.mark.nivel("medio")
def test_match_already_has_two_teams(client, db_session: Session):
    match = create_match(client, max_players=4)

    p1 = utils.create_player(client,"t1p1")
    p2 = utils.create_player(client,"t2p1")
    p1_obj = db_session.query(Player).filter(Player.id == p1).first()
    p2_obj = db_session.query(Player).filter(Player.id == p2).first()

    team1 = create_team(db_session, [p1_obj])
    team2 = create_team(db_session, [p2_obj])

    res1 = client.post(f"/match/matches/{match['id']}/teams/{team1.id}")
    assert res1.status_code == 200

    res2 = client.post(f"/match/matches/{match['id']}/teams/{team2.id}")
    assert res2.status_code == 200

    new_player_id = utils.create_player(client,"newp1")
    new_player_obj = db_session.query(Player).filter(Player.id == new_player_id).first()
    new_team = create_team(db_session, [new_player_obj])

    res3 = client.post(f"/match/matches/{match['id']}/teams/{new_team.id}")
    assert res3.status_code >= 400
