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


@pytest.mark.nivel("bajo")
def test_designed_bot_is_assigned_to_the_match_before_pool_bots(db_session):
    humans = [Player(name=f"human_{number}") for number in range(2)]
    designed_bot = Player(name="designed_bot", is_bot=True, tiro=90, ritmo=80, fisico=70, defensa=60, aura=50)
    pool_bot = Player(name="pool_bot", is_bot=True)
    db_session.add_all(humans + [designed_bot, pool_bot])
    db_session.flush()

    match = Match(date=datetime.utcnow(), max_players=4)
    db_session.add(match)
    db_session.flush()
    for player in humans + [designed_bot]:
        db_session.add(MatchPlayer(match_id=match.id, player_id=player.id))
    db_session.commit()

    result = generate_teams_for_match(match.id, db_session)
    assigned_ids = {player.id for team in (result.team1, result.team2) for player in team.players}

    assert designed_bot.id in assigned_ids
    assert all(len(team.players) == 2 for team in (result.team1, result.team2))
