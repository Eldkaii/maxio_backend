from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from starlette.responses import StreamingResponse

from src.database import get_db
from src.models import User,Match, Team, Player, MatchPlayer, TeamEnum, MatchResultReply
from src.schemas.match_schema import MatchCreate, MatchResponse, PlayerResponse, MatchReportResponse, PreSetGroupsPayload
from src.schemas.team_schema import TeamResponse
from src.services.auth_service import get_current_user, get_optional_current_user
from src.services.league_service import get_league_or_404, require_league_admin
from src.services.match_service import create_match, assign_team_to_match, assign_player_to_match, \
    get_match_balance_report, generate_teams_for_match, generate_match_card, set_pre_set_player_groups_for_match, process_pending_match_result_replies
from pydantic import BaseModel

from src.utils.balance_teams import balance_teams
from sqlalchemy import select, update
from sqlalchemy.sql import text
from collections import defaultdict
from src.utils.logger_config import app_logger as logger

router = APIRouter()

class MessageResponse(BaseModel):
    message: str

class MatchResultPayload(BaseModel):
    result: str

@router.post("/matches/{match_id}/result", tags=["matches"])
def submit_match_result(
    match_id: int,
    payload: MatchResultPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registra la respuesta del jugador, compartida con el flujo de Telegram."""
    result = payload.result.strip().lower()
    if result not in {"win", "loss"}:
        raise HTTPException(status_code=400, detail="El resultado debe ser win o loss")
    match = db.query(Match).filter(Match.id == match_id).first()
    player = current_user.player
    if not match or not player:
        raise HTTPException(status_code=404, detail="Partido o jugador no encontrado")
    if match.date > datetime.utcnow():
        raise HTTPException(status_code=400, detail="Todavía no se puede informar el resultado")
    membership = db.query(MatchPlayer).filter(
        MatchPlayer.match_id == match_id, MatchPlayer.player_id == player.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="No pertenecés a este partido")
    existing = db.query(MatchResultReply).filter_by(
        match_id=match_id, user_id=current_user.id
    ).first()
    if existing:
        return {"message": "Ya registramos tu respuesta", "result": existing.result}
    db.add(MatchResultReply(match_id=match_id, user_id=current_user.id, result=result))
    db.commit()
    process_pending_match_result_replies(db)
    return {"message": "Respuesta registrada", "result": result}

@router.post("/matches", response_model=MatchResponse, tags=["matches"])
def create_new_match(
    match_data: MatchCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Crea un nuevo match con la fecha y cantidad máxima de jugadores.
    """
    try:
        if match_data.league_id is not None:
            if current_user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Debés iniciar sesión para crear un partido de liga")
            league = get_league_or_404(db, match_data.league_id)
            if league.is_public:
                if not current_user.player:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu usuario necesita un jugador asociado")
            else:
                require_league_admin(league, current_user)
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


@router.post("/matches/{match_id}/pre-set-groups", tags=["matches"])
def set_pre_set_groups(
    match_id: int,
    payload: PreSetGroupsPayload,
    db: Session = Depends(get_db),
):
    """Mantiene juntos los grupos elegidos antes del balanceo de humanos."""
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match no encontrado")

    assigned_ids = {
        player_id for (player_id,) in db.query(MatchPlayer.player_id)
        .filter(MatchPlayer.match_id == match_id).all()
    }
    normalized_groups = []
    used_ids = set()
    for group in payload.groups:
        names = [name.strip() for name in group if name.strip()]
        if len(names) < 2:
            raise HTTPException(status_code=400, detail="Cada grupo debe tener al menos dos jugadores")
        players = db.query(Player).filter(Player.name.in_(names)).all()
        if len(players) != len(set(names)):
            raise HTTPException(status_code=400, detail="Uno o más jugadores del grupo no existen")
        ids = [player.id for player in players]
        if not set(ids).issubset(assigned_ids):
            raise HTTPException(status_code=400, detail="Todos los jugadores del grupo deben pertenecer al match")
        if used_ids.intersection(ids):
            raise HTTPException(status_code=400, detail="Un jugador no puede pertenecer a más de un grupo")
        used_ids.update(ids)
        normalized_groups.append(players)

    set_pre_set_player_groups_for_match(match, normalized_groups, db)
    return {"message": "Grupos predefinidos guardados", "groups": len(normalized_groups)}

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
