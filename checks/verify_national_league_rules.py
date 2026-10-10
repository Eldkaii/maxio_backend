"""Focused, database-free checks for national-league scoring safeguards."""

from datetime import datetime
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.schemas.match_schema import MatchCreate
from src.services.league_service import add_league_member, join_public_league
from src.services.match_service import (
    _apply_ranking_result,
    create_match,
    has_human_majority,
)


assert not has_human_majority(5, 10)
assert not has_human_majority(4, 9)
assert has_human_majority(5, 9)
assert has_human_majority(7, 10)

ranking = SimpleNamespace(
    matches_played=0,
    wins=0,
    losses=0,
    draws=0,
    win_streak=2,
    points=0,
)
_apply_ranking_result(ranking, True, apply_win_streak_bonus=False)
assert (ranking.matches_played, ranking.wins, ranking.win_streak, ranking.points) == (1, 1, 3, 3)
_apply_ranking_result(ranking, None, apply_win_streak_bonus=False)
assert (ranking.draws, ranking.win_streak, ranking.points) == (1, 0, 4)


class FakeDb:
    def get(self, _model, _league_id):
        return SimpleNamespace(is_system_managed=True)


for operation in (
    lambda: create_match(MatchCreate(date=datetime(2026, 10, 9), max_players=10, league_id=1), FakeDb()),
    lambda: add_league_member(FakeDb(), SimpleNamespace(is_system_managed=True), "humano", "member"),
    lambda: join_public_league(FakeDb(), SimpleNamespace(is_system_managed=True), SimpleNamespace()),
):
    try:
        operation()
    except HTTPException as error:
        assert error.status_code in (400, 403)
    else:
        raise AssertionError("A system-managed national league must not be selected or joined manually")

print("OK: national league requires a strict human majority and remains automatic.")
