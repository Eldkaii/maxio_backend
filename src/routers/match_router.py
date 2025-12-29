from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from starlette.responses import StreamingResponse

from src.database import get_db
from src.models import User,Match, Team, Player, MatchPlayer, TeamEnum
from src.schemas.match_schema import MatchCreate, MatchResponse, PlayerResponse, MatchReportResponse
from src.schemas.team_schema import TeamResponse
from src.services.auth_service import get_current_user
from src.services.match_service import create_match, assign_team_to_match, assign_player_to_match, \
    get_match_balance_report, generate_teams_for_match, generate_match_card
from pydantic import BaseModel

from src.utils.balance_teams import balance_teams
from sqlalchemy import select, update
from sqlalchemy.sql import text
from collections import defaultdict
from src.utils.logger_config import app_logger as logger

router = APIRouter()

class MessageResponse(BaseModel):
    message: str

@router.post("/matches", response_model=MatchResponse, tags=["matches"])
def create_new_match(
    match_data: MatchCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo match con la fecha y cantidad máxima de jugadores.
    """
    try:
        match = create_match(match_data, db)
        return match
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/matches/{match_id}/players/{player_id}", tags=["matches"],status_code=status.HTTP_200_OK)
def add_player_to_match(match_id: int, player_id: int, team: Optional[TeamEnum] = None,db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    player = db.get(Player, player_id)

    if not match or not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match o Player no encontrado")

    success = assign_player_to_match(db, match, player, team=team)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo asignar el jugador al match")

    return {"message": "Jugador asignado exitosamente"}

@router.post("/matches/{match_id}/teams/{team_id}", response_model=MessageResponse, tags=["matches"])
def assign_team(
    match_id: int,
    team_id: int,
    db: Session = Depends(get_db)
):
    """
    Asigna un team a un match verificando que existan y cumplan condiciones.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    team = db.query(Team).filter(Team.id == team_id).first()

    if not match or not team:
        raise HTTPException(status_code=404, detail="Match o Team no encontrado")

    try:
        assign_team_to_match(team, match, db)
        return {"message": "Team asignado correctamente al match"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/matches/{match_id}/generate-teams", tags=["matches"], response_model=MatchResponse)
def generate_teams(match_id: int,
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)
                   ):

    try:
        return generate_teams_for_match(match_id, db)
    except HTTPException as e:
        raise e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Se loguea el error y se lanza excepción genérica
        import logging
        logging.exception(f"Error inesperado en /generate-teams: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/matches/{match_id}/balance-report", tags=["matches"], response_model=MatchReportResponse)
def match_balance_report(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).options(
        joinedload(Match.team1).joinedload(Team.players),
        joinedload(Match.team2).joinedload(Team.players)
    ).filter(Match.id == match_id).first()

    if not match:
        #print(f"Match con id={match_id} no encontrado")
        logger.error(f"Match con id={match_id} no encontrado")
        raise HTTPException(status_code=404, detail="Match no encontrado")

    try:
        res = get_match_balance_report(match_id,db)
        logger.info(res)

        return res
    except Exception as e:
        logger.error(f"Error inesperado al obtener reporte: {e}")
        raise HTTPException(status_code=500, detail="Error interno al generar el reporte")

@router.post("/matches/{match_id}/match-card", tags=["matches"], response_model=MatchReportResponse)
def match_card(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).options(
        joinedload(Match.team1).joinedload(Team.players),
        joinedload(Match.team2).joinedload(Team.players)
    ).filter(Match.id == match_id).first()

    if not match:
        #print(f"Match con id={match_id} no encontrado")
        logger.error(f"Match con id={match_id} no encontrado")
        raise HTTPException(status_code=404, detail="Match no encontrado")

    try:
        buffer = generate_match_card(match_id,db)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="image/png"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



def serialize_team(team):
    return TeamResponse(
        id=team.id,
        name=team.name,
        players=[{"id": p.id, "username": p.name} for p in team.players]
    )