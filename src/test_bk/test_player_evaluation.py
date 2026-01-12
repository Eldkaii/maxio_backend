import pytest
from sqlalchemy.orm import Session

from src.models.player import Player
from src.models.match import Match
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
        player_id = utils.create_player(client, username)
        player = db_session.query(Player).get(player_id)
        players.append(player)

    match_id = utils.create_match(
        client,
        [p.name for p in players]
    )

    match = db_session.query(Match).get(match_id)

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
