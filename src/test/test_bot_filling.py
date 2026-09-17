from datetime import datetime

import pytest

from src.models.match import Match, MatchPlayer
from src.models.player import Player
from src.services.match_service import generate_teams_for_match


@pytest.mark.nivel("bajo")
def test_odd_real_players_are_balanced_before_bots_are_added(db_session):
    real_players = [Player(name=f"real_{number}") for number in range(7)]
    bots = [Player(name=f"bot_{number}", is_bot=True) for number in range(3)]
    db_session.add_all(real_players + bots)
    db_session.flush()

    match = Match(date=datetime.utcnow(), max_players=10)
    db_session.add(match)
    db_session.flush()
    for player in real_players:
        db_session.add(MatchPlayer(match_id=match.id, player_id=player.id))
    db_session.commit()

    result = generate_teams_for_match(match.id, db_session)
    teams = (result.team1.players, result.team2.players)
    real_counts = [sum(not player.is_bot for player in team) for team in teams]
    bot_counts = [sum(player.is_bot for player in team) for team in teams]

    assert sorted(real_counts) == [3, 4]
    assert sorted(bot_counts) == [1, 2]
    assert all(len(team) == 5 for team in teams)
