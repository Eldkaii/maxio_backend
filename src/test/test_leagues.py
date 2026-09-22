import pytest
from fastapi import HTTPException

from src.models import Player, User
from src.services.league_service import (
    add_league_member, create_league, get_league_or_404, join_public_league,
    leave_public_league, ensure_country_leagues, list_player_leagues, require_league_admin,
    toggle_player_league_pin,
)
from src.services.match_service import league_real_player_requirement


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

    league = create_league(db_session, owner, "Liga de prueba", "solo_duo")
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
    league = create_league(db_session, owner, "Liga pública", "grupo", is_public=True)

    league = join_public_league(db_session, league, participant)
    assert {member.player_id for member in league.members} == {owner.player.id, participant.player.id}

    leave_public_league(db_session, league, participant)
    reloaded = get_league_or_404(db_session, league.id)
    assert [member.player_id for member in reloaded.members] == [owner.player.id]


@pytest.mark.nivel("bajo")
def test_ten_player_league_match_requires_three_and_four_real_players():
    assert league_real_player_requirement(10) == (7, 3)


@pytest.mark.nivel("bajo")
def test_uruguay_national_league_enrolls_players_and_cannot_be_left(db_session):
    player_user = make_user_and_player(db_session, "uruguay_player")
    leagues = ensure_country_leagues(db_session, "UY")
    db_session.commit()
    assert {league.league_type for league in leagues} == {"solo_duo", "grupo"}
    league = get_league_or_404(db_session, next(league.id for league in leagues if league.league_type == "grupo"))

    assert league.is_public is True
    assert league.is_system_managed is True
    assert league.country_code == "UY"
    assert {member.player_id for member in league.members} == {player_user.player.id}
    with pytest.raises(HTTPException) as error:
        leave_public_league(db_session, league, player_user)
    assert error.value.status_code == 403


@pytest.mark.nivel("bajo")
def test_player_can_create_only_three_leagues_unless_global_admin(db_session):
    owner = make_user_and_player(db_session, "limited_owner")
    for index in range(3):
        create_league(db_session, owner, f"Liga limitada {index}", "grupo")
    with pytest.raises(HTTPException) as error:
        create_league(db_session, owner, "Liga limitada extra", "grupo")
    assert error.value.status_code == 403

    owner.is_admin = True
    db_session.commit()
    assert create_league(db_session, owner, "Liga de administrador", "grupo").owner_player_id == owner.player.id


@pytest.mark.nivel("bajo")
def test_pinning_a_league_places_it_first_for_the_player(db_session):
    owner = make_user_and_player(db_session, "pin_owner")
    first = create_league(db_session, owner, "Liga sin pin", "grupo")
    second = create_league(db_session, owner, "Liga fijada", "solo_duo")

    toggle_player_league_pin(db_session, second.id, owner)
    leagues = list_player_leagues(db_session, owner)
    assert leagues[0]["id"] == second.id
    assert leagues[0]["is_pinned"] is True
    assert next(league for league in leagues if league["id"] == first.id)["is_pinned"] is False
