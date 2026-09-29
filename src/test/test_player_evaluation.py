import pytest
from sqlalchemy.orm import Session

from src.models.player import Player
from src.models.match import Match, MatchPlayer
from src.models.player_evaluation import PlayerEvaluationPermission
from src.services.player_evaluation_service import (
    create_evaluation_permissions_from_match,
    can_player_evaluate,
)
from src.test.utils_common_methods import TestUtils

utils = TestUtils()


@pytest.fixture(scope="function")
def setup_match_with_players(client, db_session: Session):
    usernames = ["Alice", "Bob", "Charlie", "Diana"]

    players = []
    for username in usernames:
        user_id = utils.create_player(client, username)
        player = db_session.query(Player).filter(Player.user_id == user_id).one()
        players.append(player)

    assert all(player.is_bot is False for player in players)

    # El helper create_match recibe max_players; para este test de permisos
    # alcanza con asociar explícitamente los jugadores al partido.
    match = Match(max_players=len(players))
    db_session.add(match)
    db_session.flush()
    for player in players:
        db_session.add(MatchPlayer(match_id=match.id, player_id=player.id))
    db_session.commit()
    db_session.refresh(match)
    match_id = match.id
    assert db_session.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).count() == len(players)

    yield {
        "players": players,
        "match": match,
    }

    # Cleanup
    db_session.query(PlayerEvaluationPermission).delete()
    db_session.query(Match).filter(Match.id == match_id).delete()
    db_session.query(Player).filter(Player.id.in_([p.id for p in players])).delete()
    db_session.commit()

@pytest.mark.nivel("bajo")
def test_create_evaluation_permissions_from_match_creates_all_pairs(
    setup_match_with_players,
    db_session: Session
):
    players = setup_match_with_players["players"]
    match = setup_match_with_players["match"]

    create_evaluation_permissions_from_match(db_session, match.id)

    expected_count = len(players) * (len(players) - 1)

    perms = db_session.query(PlayerEvaluationPermission).all()
    assert len(perms) == expected_count

@pytest.mark.nivel("bajo")
def test_no_self_evaluation_permissions_created(
    setup_match_with_players,
    db_session: Session
):
    match = setup_match_with_players["match"]

    create_evaluation_permissions_from_match(db_session, match.id)

    invalid = db_session.query(PlayerEvaluationPermission).filter(
        PlayerEvaluationPermission.evaluator_id ==
        PlayerEvaluationPermission.target_id
    ).all()

    assert invalid == []

@pytest.mark.nivel("bajo")
def test_can_player_evaluate_returns_true_only_when_permission_exists(
    setup_match_with_players,
    db_session: Session
):
    players = setup_match_with_players["players"]
    match = setup_match_with_players["match"]

    p1, p2 = players[0], players[1]

    # Antes de crear permisos
    assert can_player_evaluate(db_session, p1.id, p2.id) is False

    create_evaluation_permissions_from_match(db_session, match.id)

    assert can_player_evaluate(db_session, p1.id, p2.id) is True
    assert can_player_evaluate(db_session, p2.id, p1.id) is True
