import pytest
from fastapi import HTTPException

from src.models import LeagueRanking, Player, User
from src.services.league_service import (
    add_league_member, create_league, get_league_or_404, join_public_league,
    leave_public_league, ensure_country_leagues, list_player_leagues, require_league_admin,
    toggle_player_league_pin,
    division_for_points, sync_player_country_league,
)
from src.services.match_service import _apply_ranking_result, league_real_player_requirement


def make_user_and_player(db_session, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password="unused",
        password_test="unused",
    )
    player = Player(name=username, user=user)
    db_session.add(player)
    db_session.commit()
    return user


@pytest.mark.nivel("bajo")
def test_league_creator_becomes_owner_and_admin(db_session):
    owner = make_user_and_player(db_session, "league_owner")
    participant = make_user_and_player(db_session, "league_participant")
    outsider = make_user_and_player(db_session, "league_outsider")

    league = create_league(db_session, owner, "Liga de prueba")
    assert league.owner_player_id == owner.player.id
    assert [(member.player_id, member.role) for member in league.members] == [(owner.player.id, "admin")]

    league = add_league_member(db_session, league, participant.username, "admin")
    reloaded = get_league_or_404(db_session, league.id)
    assert {(member.player_id, member.role) for member in reloaded.members} == {
        (owner.player.id, "admin"),
        (participant.player.id, "admin"),
    }
    require_league_admin(reloaded, participant)
    with pytest.raises(HTTPException) as error:
        require_league_admin(reloaded, outsider)
    assert error.value.status_code == 403


@pytest.mark.nivel("bajo")
def test_public_league_allows_self_join_and_leave(db_session):
    owner = make_user_and_player(db_session, "public_owner")
    participant = make_user_and_player(db_session, "public_participant")
    league = create_league(db_session, owner, "Liga pública", is_public=True)

    league = join_public_league(db_session, league, participant)
    assert {member.player_id for member in league.members} == {owner.player.id, participant.player.id}

    leave_public_league(db_session, league, participant)
    reloaded = get_league_or_404(db_session, league.id)
    assert [member.player_id for member in reloaded.members] == [owner.player.id]


@pytest.mark.nivel("bajo")
def test_ten_player_league_match_requires_three_and_four_real_players():
    assert league_real_player_requirement(10) == (7, 3)


@pytest.mark.nivel("bajo")
def test_league_divisions_use_the_defined_point_boundaries():
    assert [division_for_points(points) for points in (0, 14, 15, 39, 40, 79, 80)] == [
        "Bronce", "Bronce", "Plata", "Plata", "Oro", "Oro", "Diamante",
    ]


@pytest.mark.nivel("bajo")
def test_uruguay_national_league_enrolls_players_and_cannot_be_left(db_session):
    player_user = make_user_and_player(db_session, "uruguay_player")
    leagues = ensure_country_leagues(db_session, "UY")
    db_session.commit()
    assert len(leagues) == 1
    league = get_league_or_404(db_session, leagues[0].id)

    assert league.is_public is True
    assert league.is_system_managed is True
    assert league.country_code == "UY"
    assert {member.player_id for member in league.members} == {player_user.player.id}
    with pytest.raises(HTTPException) as error:
        leave_public_league(db_session, league, player_user)
    assert error.value.status_code == 403


@pytest.mark.nivel("bajo")
def test_syncing_country_league_twice_does_not_duplicate_memberships(db_session):
    player_user = make_user_and_player(db_session, "uruguay_sync_player")
    player_user.nationality = "UY"
    db_session.flush()

    sync_player_country_league(db_session, player_user.player, "UY")
    sync_player_country_league(db_session, player_user.player, "UY")
    db_session.flush()

    for league in ensure_country_leagues(db_session, "UY"):
        memberships = [
            member for member in league.members
            if member.player_id == player_user.player.id
        ]
        assert len(memberships) == 1


@pytest.mark.nivel("bajo")
def test_player_can_create_only_three_leagues_unless_global_admin(db_session):
    owner = make_user_and_player(db_session, "limited_owner")
    for index in range(3):
        create_league(db_session, owner, f"Liga limitada {index}")
    with pytest.raises(HTTPException) as error:
        create_league(db_session, owner, "Liga limitada extra")
    assert error.value.status_code == 403

    owner.is_admin = True
    db_session.commit()
    assert create_league(db_session, owner, "Liga de administrador").owner_player_id == owner.player.id


@pytest.mark.nivel("bajo")
def test_pinning_a_league_places_it_first_for_the_player(db_session):
    owner = make_user_and_player(db_session, "pin_owner")
    first = create_league(db_session, owner, "Liga sin pin")
    second = create_league(db_session, owner, "Liga fijada")

    toggle_player_league_pin(db_session, second.id, "solo_duo", owner)
    leagues = list_player_leagues(db_session, owner)
    second_ranking = next(item for item in next(league for league in leagues if league["id"] == second.id)["rankings"] if item["ranking_type"] == "solo_duo")
    first_ranking = next(item for item in next(league for league in leagues if league["id"] == first.id)["rankings"] if item["ranking_type"] == "solo_duo")
    assert second_ranking["is_pinned"] is True
    assert first_ranking["is_pinned"] is False


@pytest.mark.nivel("bajo")
def test_every_league_member_has_general_solo_duo_and_group_rankings(db_session):
    owner = make_user_and_player(db_session, "rankings_owner")
    league = create_league(db_session, owner, "Liga con tres rankings", max_group_size=2)

    rankings = db_session.query(LeagueRanking).filter(
        LeagueRanking.league_member_id == league.members[0].id,
    ).all()
    assert {ranking.ranking_type for ranking in rankings} == {"general", "solo_duo", "grupo"}
    assert league.max_group_size == 2


@pytest.mark.nivel("bajo")
def test_ranking_points_and_streak_bonuses_follow_the_league_rules(db_session):
    owner = make_user_and_player(db_session, "streak_owner")
    league = create_league(db_session, owner, "Liga de rachas")
    ranking = next(item for item in league.members[0].rankings if item.ranking_type == "general")

    for _ in range(3):
        _apply_ranking_result(ranking, won=True)
    assert (ranking.points, ranking.win_streak, ranking.wins) == (12, 3, 3)
    for _ in range(2):
        _apply_ranking_result(ranking, won=True)
    assert (ranking.points, ranking.win_streak) == (23, 5)
    for _ in range(2):
        _apply_ranking_result(ranking, won=True)
    assert (ranking.points, ranking.win_streak) == (39, 7)
    _apply_ranking_result(ranking, won=False)
    assert (ranking.points, ranking.win_streak, ranking.losses) == (38, 0, 1)


@pytest.mark.nivel("bajo")
def test_league_api_exposes_the_three_rankings(db_session, client):
    owner = make_user_and_player(db_session, "league_api_owner")
    league = create_league(db_session, owner, "Liga API")

    response = client.get(f"/leagues/{league.id}")
    assert response.status_code == 200
    member = response.json()["members"][0]
    assert {ranking["ranking_type"] for ranking in member["rankings"]} == {
        "general", "solo_duo", "grupo",
    }
