from datetime import datetime

import pytest

from src.models.match import Match, MatchPlayer, TeamEnum
from src.models.player import Player
from src.models.player_evaluation import PlayerEvaluationPermission
from src.services.player_evaluation_service import (
    can_player_evaluate,
    create_evaluation_permissions_from_match,
)


def _match_with_players(db_session, players, *, preset_groups=None):
    match = Match(
        date=datetime.utcnow(),
        max_players=len(players),
        pre_set_groups=preset_groups or [],
    )
    db_session.add(match)
    db_session.flush()

    midpoint = len(players) // 2
    for index, player in enumerate(players):
        db_session.add(
            MatchPlayer(
                match_id=match.id,
                player_id=player.id,
                team=TeamEnum.team1 if index < midpoint else TeamEnum.team2,
            )
        )
    db_session.commit()
    return match


@pytest.mark.nivel("bajo")
def test_permissions_are_created_for_human_pairs_except_preset_teammates(db_session):
    players = [Player(name=f"eval_pair_{index}") for index in range(4)]
    db_session.add_all(players)
    db_session.flush()
    match = _match_with_players(
        db_session,
        players,
        # Estos dos jugadores fueron unidos explícitamente al armar el partido.
        preset_groups=[[players[0].id, players[1].id]],
    )

    create_evaluation_permissions_from_match(db_session, match.id)

    permissions = db_session.query(PlayerEvaluationPermission).all()
    directed_pairs = {
        (permission.evaluator_id, permission.target_id)
        for permission in permissions
    }

    # 4 jugadores producen 12 pares dirigidos; se excluyen las dos direcciones
    # del grupo preconfigurado y no se crean permisos para bots.
    assert len(directed_pairs) == 10
    assert (players[0].id, players[1].id) not in directed_pairs
    assert (players[1].id, players[0].id) not in directed_pairs
    assert (players[0].id, players[2].id) in directed_pairs
    assert (players[2].id, players[0].id) in directed_pairs


@pytest.mark.nivel("bajo")
def test_existing_permission_is_preserved_for_new_preset_group(db_session):
    players = [Player(name=f"eval_keep_{index}") for index in range(3)]
    db_session.add_all(players)
    db_session.flush()

    old_permission = PlayerEvaluationPermission(
        evaluator_id=players[0].id,
        target_id=players[1].id,
    )
    db_session.add(old_permission)
    db_session.commit()

    match = _match_with_players(
        db_session,
        players,
        preset_groups=[[players[0].id, players[1].id]],
    )
    create_evaluation_permissions_from_match(db_session, match.id)

    assert can_player_evaluate(db_session, players[0].id, players[1].id)
    assert db_session.query(PlayerEvaluationPermission).filter_by(
        evaluator_id=players[0].id,
        target_id=players[1].id,
    ).count() == 1
    assert can_player_evaluate(db_session, players[0].id, players[2].id)


@pytest.mark.nivel("bajo")
def test_multiple_matches_do_not_duplicate_global_pair_permission(db_session):
    players = [Player(name=f"eval_repeat_{index}") for index in range(4)]
    db_session.add_all(players)
    db_session.flush()

    first_match = _match_with_players(db_session, players)
    second_match = _match_with_players(db_session, players)

    create_evaluation_permissions_from_match(db_session, first_match.id)
    create_evaluation_permissions_from_match(db_session, second_match.id)

    expected_pairs = len(players) * (len(players) - 1)
    assert db_session.query(PlayerEvaluationPermission).count() == expected_pairs
    assert db_session.query(PlayerEvaluationPermission).filter_by(
        evaluator_id=players[0].id,
        target_id=players[1].id,
    ).count() == 1
