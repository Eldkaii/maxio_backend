import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.models import LeagueRanking
from src.models.match_result_reply import MatchResultReply
from src.services.match_service import (
    _apply_ranking_result,
    process_pending_match_result_replies,
    try_close_match_if_ready,
)
from src.services.player_service import build_full_player_profile
from src.test.utils_common_methods import TestUtils


utils = TestUtils()
client = TestClient(app)


def _create_match_with_draw_replies(client: TestClient, db_session: Session, replies: int | None = None):
    """Crea un partido balanceado y registra votos de empate para sus jugadores."""
    match, team1, team2 = utils.create_balanced_match(client, db_session, players_per_team=2)
    players = team1.players + team2.players

    for player in players[:replies]:
        assert player.user is not None
        db_session.add(MatchResultReply(
            match_id=match.id,
            user_id=player.user.id,
            result="draw",
            pending=True,
        ))
    db_session.commit()
    return match, team1, team2, players


@pytest.mark.nivel("medio")
def test_match_closes_as_draw_when_all_players_vote_draw(
    client: TestClient,
    db_session: Session,
):
    match, _, _, players = _create_match_with_draw_replies(client, db_session, replies=4)

    assert process_pending_match_result_replies(db_session) == len(players)
    assert try_close_match_if_ready(match, db_session) is True

    db_session.refresh(match)
    assert match.is_draw is True
    assert match.winner_team_id is None
    assert match.vote_draw == len(players)


@pytest.mark.nivel("medio")
def test_draw_can_close_with_an_irreversible_majority(
    client: TestClient,
    db_session: Session,
):
    match, _, _, players = _create_match_with_draw_replies(client, db_session, replies=3)

    process_pending_match_result_replies(db_session)

    # Queda un voto por emitir: ya no puede alcanzar ni superar los tres empates.
    assert try_close_match_if_ready(match, db_session) is True

    db_session.refresh(match)
    assert match.is_draw is True
    assert match.winner_team_id is None
    assert match.vote_draw == 3
    assert players[0].cant_partidos_empatados == 1


@pytest.mark.nivel("medio")
def test_match_stays_open_when_draw_has_no_strict_majority(
    client: TestClient,
    db_session: Session,
):
    match, _, _, _ = _create_match_with_draw_replies(client, db_session, replies=1)

    process_pending_match_result_replies(db_session)

    assert try_close_match_if_ready(match, db_session) is False
    db_session.refresh(match)
    assert match.is_draw is False
    assert match.winner_team_id is None


@pytest.mark.nivel("medio")
def test_draw_updates_player_history_profile_and_league_ranking(
    client: TestClient,
    db_session: Session,
):
    match, team1, _, _ = _create_match_with_draw_replies(client, db_session, replies=4)

    process_pending_match_result_replies(db_session)
    assert try_close_match_if_ready(match, db_session) is True

    player = team1.players[0]
    db_session.refresh(player)
    profile = build_full_player_profile(db_session, player.name)

    assert player.cant_partidos == 1
    assert player.cant_partidos_ganados == 0
    assert player.cant_partidos_empatados == 1
    assert player.recent_results == ["draw"]
    assert profile["matches_summary"]["drawn"] == 1
    assert profile["recent_matches"][0]["result"] == "draw"

    ranking = LeagueRanking(points=7, matches_played=2, wins=2, losses=0, draws=0, win_streak=2)
    _apply_ranking_result(ranking, won=None)
    assert ranking.points == 8
    assert ranking.matches_played == 3
    assert ranking.draws == 1
    assert ranking.win_streak == 0
