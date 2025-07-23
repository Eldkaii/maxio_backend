from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.schemas.player_schema import PlayerResponse, PlayerStatsUpdate, RelatedPlayerResponse
from src.services.player_service import get_player_by_username,update_player_stats
from src.database import get_db
from typing import List

router = APIRouter()

@router.get("/{username}", response_model=PlayerResponse, tags=["players"])
def read_player(username: str, db: Session = Depends(get_db)):
    try:
        player = get_player_by_username(username, db)
        return player
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{target_username}/stats", tags=["players"])
def set_player_stats(
    target_username: str,
    evaluator_username: str,
    stats: PlayerStatsUpdate,
    db: Session = Depends(get_db)
):
    try:
        updated_player = update_player_stats(
            target_username=target_username,
            evaluator_username=evaluator_username,
            stats_data=stats,
            db=db
        )
        return {"message": "Stats actualizados correctamente", "player": updated_player.name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{username}/top_teammates", response_model=List[RelatedPlayerResponse])
def get_top_teammates(
    username: str,
    limit: int = Query(5, ge=1, le=20),
    exclude_bots: bool = Query(False),
    db: Session = Depends(get_db)
):
    try:
        player = get_player_by_username(username, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    data = player.top_teammates(db, limit=limit, exclude_bots=exclude_bots)
    return [
        RelatedPlayerResponse(
            id=p.id,
            name=p.name,
            cant_partidos=p.cant_partidos,
            elo=p.elo,
            punteria=p.punteria,
            velocidad=p.velocidad,
            dribbling=p.dribbling,
            defensa=p.defensa,
            magia=p.magia,
            games=games
        )
        for p, games in data
    ]

@router.get("/{username}/top_allies", response_model=List[RelatedPlayerResponse])
def get_top_allies(
    username: str,
    limit: int = Query(3, ge=1, le=20),
    exclude_bots: bool = Query(False),
    db: Session = Depends(get_db)
):
    try:
        player = get_player_by_username(username, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    data = player.top_allies(db, limit=limit, exclude_bots=exclude_bots)
    return [
        RelatedPlayerResponse(
            id=p.id,
            name=p.name,
            cant_partidos=p.cant_partidos,
            elo=p.elo,
            punteria=p.punteria,
            velocidad=p.velocidad,
            dribbling=p.dribbling,
            defensa=p.defensa,
            magia=p.magia,
            games=games
        )
        for p, games in data
    ]


@router.get("/{username}/top_opponents", response_model=List[RelatedPlayerResponse])
def get_top_opponents(
    username: str,
    limit: int = Query(3, ge=1, le=20),
    exclude_bots: bool = Query(False),
    db: Session = Depends(get_db)
):
    try:
        player = get_player_by_username(username, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    data = player.top_opponents(db, limit=limit, exclude_bots=exclude_bots)
    return [
        RelatedPlayerResponse(
            id=p.id,
            name=p.name,
            cant_partidos=p.cant_partidos,
            elo=p.elo,
            punteria=p.punteria,
            velocidad=p.velocidad,
            dribbling=p.dribbling,
            defensa=p.defensa,
            magia=p.magia,
            games=games
        )
        for p, games in data
    ]