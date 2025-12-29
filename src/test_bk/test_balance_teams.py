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
        ("Alice", {"tiro": 80, "ritmo": 90, "fisico": 85, "defensa": 70, "aura": 75}),
        ("Bob", {"tiro": 78, "ritmo": 88, "fisico": 82, "defensa": 72, "aura": 70}),
        ("Charlie", {"tiro": 50, "ritmo": 60, "fisico": 55, "defensa": 65, "aura": 40}),
        ("Diana", {"tiro": 45, "ritmo": 55, "fisico": 50, "defensa": 60, "aura": 35}),
        ("Eddie", {"tiro": 88, "ritmo": 85, "fisico": 90, "defensa": 80, "aura": 95}),
        ("Fiona", {"tiro": 83, "ritmo": 82, "fisico": 88, "defensa": 78, "aura": 90}),
        ("Leo", {"tiro": 75, "ritmo": 70, "fisico": 72, "defensa": 65, "aura": 68}),
        ("Max", {"tiro": 78, "ritmo": 74, "fisico": 69, "defensa": 70, "aura": 72}),
        ("Nia", {"tiro": 73, "ritmo": 68, "fisico": 75, "defensa": 66, "aura": 65}),
        ("Ola", {"tiro": 80, "ritmo": 72, "fisico": 70, "defensa": 68, "aura": 70}),
        ("Paz", {"tiro": 77, "ritmo": 69, "fisico": 74, "defensa": 67, "aura": 69}),
        ("Rex", {"tiro": 70, "ritmo": 75, "fisico": 68, "defensa": 69, "aura": 66}),
        ("Sol", {"tiro": 74, "ritmo": 73, "fisico": 71, "defensa": 64, "aura": 67}),
        ("Tia", {"tiro": 76, "ritmo": 70, "fisico": 73, "defensa": 65, "aura": 68}),
        ("Ula", {"tiro": 72, "ritmo": 71, "fisico": 69, "defensa": 66, "aura": 65}),
        ("Val", {"tiro": 79, "ritmo": 74, "fisico": 70, "defensa": 67, "aura": 70}),
        ("Wes", {"tiro": 71, "ritmo": 72, "fisico": 68, "defensa": 65, "aura": 66}),
        ("Yas", {"tiro": 75, "ritmo": 73, "fisico": 72, "defensa": 68, "aura": 69}),
        ("Zoe", {"tiro": 73, "ritmo": 70, "fisico": 71, "defensa": 66, "aura": 67}),
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
