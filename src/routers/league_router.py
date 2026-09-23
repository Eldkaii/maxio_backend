from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import League
from src.schemas.league_schema import LeagueCreate, LeagueMemberCreate, LeagueMemberRoleUpdate, LeagueResponse, MyLeagueResponse
from src.services.auth_service import get_current_user
from src.services.league_service import (
    add_league_member, create_league, get_league_or_404, remove_league_member,
    join_public_league, leave_public_league, list_player_leagues, require_league_admin, serialize_league,
    toggle_player_league_pin, update_league_member_role,
)


router = APIRouter(prefix="/leagues", tags=["leagues"])


@router.get("/mine", response_model=list[MyLeagueResponse])
def list_my_leagues(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return list_player_leagues(db, current_user)


@router.get("", response_model=list[LeagueResponse])
def list_leagues(db: Session = Depends(get_db)):
    leagues = db.query(League).order_by(League.name.asc()).all()
    return [serialize_league(get_league_or_404(db, league.id)) for league in leagues]


@router.get("/{league_id}", response_model=LeagueResponse)
def read_league(league_id: int, db: Session = Depends(get_db)):
    return serialize_league(get_league_or_404(db, league_id))


@router.post("", response_model=LeagueResponse, status_code=status.HTTP_201_CREATED)
def create_new_league(
    payload: LeagueCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return serialize_league(create_league(
        db, current_user, payload.name, payload.is_public, payload.is_special, payload.max_group_size,
    ))


@router.put("/{league_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
def toggle_league_pin(
    league_id: int,
    ranking_type: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    toggle_player_league_pin(db, league_id, ranking_type, current_user)


@router.post("/{league_id}/join", response_model=LeagueResponse)
def join_league(
    league_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return serialize_league(join_public_league(db, get_league_or_404(db, league_id), current_user))


@router.delete("/{league_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_league(
    league_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    leave_public_league(db, get_league_or_404(db, league_id), current_user)


@router.post("/{league_id}/members", response_model=LeagueResponse)
def add_member(
    league_id: int,
    payload: LeagueMemberCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    league = get_league_or_404(db, league_id)
    require_league_admin(league, current_user)
    return serialize_league(add_league_member(db, league, payload.username, payload.role))


@router.put("/{league_id}/members/{player_id}/role", response_model=LeagueResponse)
def change_member_role(
    league_id: int,
    player_id: int,
    payload: LeagueMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    league = get_league_or_404(db, league_id)
    require_league_admin(league, current_user)
    return serialize_league(update_league_member_role(db, league, player_id, payload.role))


@router.delete("/{league_id}/members/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    league_id: int,
    player_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    league = get_league_or_404(db, league_id)
    require_league_admin(league, current_user)
    remove_league_member(db, league, player_id)
