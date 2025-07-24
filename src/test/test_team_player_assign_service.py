import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.models import Team
from src.services.team_service import assign_team_players
from src.test.utils_common_methods import TestUtils


@pytest.fixture
def test_utils():
    return TestUtils()


@pytest.fixture
def setup_team_and_players(client: TestClient, db_session: Session, test_utils: TestUtils):
    usernames = ["Alice", "Bob", "Charlie"]
    player_ids = test_utils.create_players(client, usernames)

    # Traer los jugadores ORM directamente usando db_session
    from src.models.player import Player
    players = db_session.query(Player).filter(Player.name.in_(usernames)).all()

    team_id = test_utils.create_team(db_session, player_ids=[], name="Equipo Test")
    team = test_utils.get_team_by_id(db_session, team_id)

    return {
        "team": team,
        "player_ids": player_ids,
        "players": players,  # lista ORM real
        "usernames": usernames
    }

def test_assign_players_by_ids(db_session: Session, setup_team_and_players):
    team = setup_team_and_players["team"]
    player_ids = setup_team_and_players["player_ids"]

    updated_team = assign_team_players(db_session, team_id=team.id, player_ids=player_ids)

    assert updated_team.id == team.id
    assert len(updated_team.players) == len(player_ids)
    assert sorted([p.id for p in updated_team.players]) == sorted(player_ids)


def test_assign_players_by_usernames(db_session: Session, setup_team_and_players, client: TestClient, test_utils: TestUtils):
    team = setup_team_and_players["team"]
    usernames = setup_team_and_players["usernames"]

    # Validamos que todos los jugadores existen en el sistema
    for username in usernames:
        test_utils.get_player(client, username)

    updated_team = assign_team_players(db_session, team_id=team.id, player_usernames=usernames)

    assert updated_team.id == team.id
    assert len(updated_team.players) == len(usernames)
    assert sorted([p.name for p in updated_team.players]) == sorted(usernames)


def test_assign_players_mixed_no_duplicates(db_session: Session, setup_team_and_players):
    team = setup_team_and_players["team"]
    players = setup_team_and_players["players"]  # objetos Player completos
    usernames = setup_team_and_players["usernames"]

    # Usar IDs reales para evitar inconsistencias
    player_ids = [p.id for p in players]

    # Simular mezcla: primero dos IDs, y dos usernames (incluyendo uno repetido)
    mixed_ids = player_ids[:2]                       # IDs de Alice y Bob
    mixed_usernames = [players[1].name, players[2].name]  # usernames Bob y Charlie

    updated_team = assign_team_players(
        db=db_session,
        team_id=team.id,
        player_ids=mixed_ids,
        player_usernames=mixed_usernames
    )

    # Validamos que solo hay 3 jugadores únicos (Alice, Bob, Charlie)
    assert updated_team.id == team.id
    assert len(updated_team.players) == 3

    actual_names = sorted([p.name for p in updated_team.players])
    assert actual_names == sorted(usernames)