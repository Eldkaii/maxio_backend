import pytest
from src.utils.balance_teams import balance_teams
from src.services.player_service import add_player_relation
from sqlalchemy.orm import Session
from src.models.player import PlayerRelation, Player
from src.database import get_db
from src.test.utils_common_methods import TestUtils

utils = TestUtils()

@pytest.fixture(scope="function")
def setup_players(client, db_session: Session):
    usernames = [
        ("Alice", {"punteria": 80, "velocidad": 90, "resistencia": 85, "defensa": 70, "magia": 75}),
        ("Bob", {"punteria": 78, "velocidad": 88, "resistencia": 82, "defensa": 72, "magia": 70}),
        ("Charlie", {"punteria": 50, "velocidad": 60, "resistencia": 55, "defensa": 65, "magia": 40}),
        ("Diana", {"punteria": 45, "velocidad": 55, "resistencia": 50, "defensa": 60, "magia": 35}),
        ("Eddie", {"punteria": 88, "velocidad": 85, "resistencia": 90, "defensa": 80, "magia": 95}),
        ("Fiona", {"punteria": 83, "velocidad": 82, "resistencia": 88, "defensa": 78, "magia": 90}),
        ("Leo", {"punteria": 75, "velocidad": 70, "resistencia": 72, "defensa": 65, "magia": 68}),
        ("Max", {"punteria": 78, "velocidad": 74, "resistencia": 69, "defensa": 70, "magia": 72}),
        ("Nia", {"punteria": 73, "velocidad": 68, "resistencia": 75, "defensa": 66, "magia": 65}),
        ("Ola", {"punteria": 80, "velocidad": 72, "resistencia": 70, "defensa": 68, "magia": 70}),
        ("Paz", {"punteria": 77, "velocidad": 69, "resistencia": 74, "defensa": 67, "magia": 69}),
        ("Rex", {"punteria": 70, "velocidad": 75, "resistencia": 68, "defensa": 69, "magia": 66}),
        ("Sol", {"punteria": 74, "velocidad": 73, "resistencia": 71, "defensa": 64, "magia": 67}),
        ("Tia", {"punteria": 76, "velocidad": 70, "resistencia": 73, "defensa": 65, "magia": 68}),
        ("Ula", {"punteria": 72, "velocidad": 71, "resistencia": 69, "defensa": 66, "magia": 65}),
        ("Val", {"punteria": 79, "velocidad": 74, "resistencia": 70, "defensa": 67, "magia": 70}),
        ("Wes", {"punteria": 71, "velocidad": 72, "resistencia": 68, "defensa": 65, "magia": 66}),
        ("Yas", {"punteria": 75, "velocidad": 73, "resistencia": 72, "defensa": 68, "magia": 69}),
        ("Zoe", {"punteria": 73, "velocidad": 70, "resistencia": 71, "defensa": 66, "magia": 67}),
    ]

    players = {}

    for username, stats in usernames:
        player_id = utils.create_player(client, username)
        player = db_session.query(Player).filter_by(id=player_id).first()
        for stat, val in stats.items():
            setattr(player, stat, val)
        db_session.commit()
        players[username] = player

    # Crear relaciones usando add_player_relation
    add_player_relation(players["Alice"].id, players["Bob"].id, together=True, db=db_session)
    add_player_relation(players["Charlie"].id, players["Diana"].id, together=True, db=db_session)
    add_player_relation(players["Eddie"].id, players["Fiona"].id, together=True, db=db_session)
    add_player_relation(players["Alice"].id, players["Charlie"].id, together=False, db=db_session)
    add_player_relation(players["Bob"].id, players["Diana"].id, together=False, db=db_session)
    add_player_relation(players["Eddie"].id, players["Alice"].id, together=False, db=db_session)

    yield players

    # Cleanup
    db_session.query(PlayerRelation).delete()
    db_session.query(Player).filter(Player.id.in_([p.id for p in players.values()])).delete()
    db_session.commit()


def assert_group_preserved(group, team1, team2):
    team1_ids = {p.id for p in team1}
    team2_ids = {p.id for p in team2}
    ids = {p.id for p in group}
    assert ids.issubset(team1_ids) or ids.issubset(team2_ids), f"Grupo fue dividido: {[p.name for p in group]}"


@pytest.mark.nivel("medio")
def test_balance_teams_with_detailed_output(setup_players):
    players = setup_players
    groups = [
        [players["Alice"], players["Bob"]],
        [players["Charlie"], players["Diana"]],
        [players["Eddie"]],
        [players["Fiona"]],
    ]
    team1, team2 = balance_teams(groups)
    # Aquí podés agregar asserts o simplemente imprimir para debug
    #print("✅ test_balance_teams_with_detailed_output finalizado correctamente")


@pytest.mark.nivel("medio")
def test_one_group_and_solos(setup_players):
    players = setup_players
    groups = [
        [players["Leo"], players["Max"], players["Nia"]],
        [players["Ola"]],
        [players["Paz"]],
        [players["Rex"]],
    ]
    team1, team2 = balance_teams(groups)
    assert_group_preserved(groups[0], team1, team2)


@pytest.mark.nivel("medio")
def test_two_groups_and_solos(setup_players):
    players = setup_players
    groups = [
        [players["Sol"], players["Tia"], players["Ula"]],
        [players["Val"], players["Wes"]],
        [players["Yas"]],
        [players["Zoe"]],
        [players["Rex"]],
    ]
    team1, team2 = balance_teams(groups)
    assert_group_preserved(groups[0], team1, team2)
    assert_group_preserved(groups[1], team1, team2)


@pytest.mark.nivel("medio")
def test_all_individuals(setup_players):
    players = setup_players
    indiv_players = [players[name] for name in ["Leo", "Max", "Nia", "Ola", "Paz", "Rex"]]
    groups = [[p] for p in indiv_players]
    team1, team2 = balance_teams(groups)
    assert len(team1) == len(team2)
    #print("✅ test_all_individuals finalizado correctamente")
