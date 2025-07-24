from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from src.database import get_db
from src.models import Match, Team, Player, MatchPlayer, TeamEnum
from src.schemas.match_schema import MatchCreate, MatchResponse, PlayerResponse, MatchReportResponse
from src.schemas.team_schema import TeamResponse
from src.services.match_service import create_match, assign_team_to_match, assign_player_to_match, \
    get_match_balance_report
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
def add_player_to_match(match_id: int, player_id: int, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    player = db.get(Player, player_id)

    if not match or not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match o Player no encontrado")

    success = assign_player_to_match(db, match, player)

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
def generate_teams(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).options(
        joinedload(Match.team1).joinedload(Team.players),
        joinedload(Match.team2).joinedload(Team.players)
    ).filter(Match.id == match_id).first()

    if not match:
        logger.error(f"Match con id={match_id} no encontrado")
        raise HTTPException(status_code=404, detail="Match no encontrado")

    try:
        # Obtener players y su team asignado en MatchPlayer
        rows = db.execute(
            select(Player, MatchPlayer.team)
            .join(MatchPlayer, MatchPlayer.player_id == Player.id)
            .where(MatchPlayer.match_id == match.id)
        ).all()

        if not rows:
            logger.warning(f"No hay jugadores asignados al match {match_id}")
            raise HTTPException(status_code=400, detail="No hay jugadores asignados al match")

        # Separar jugadores en grupos según team, o individuales si no tienen team asignado (None)
        groups_dict = defaultdict(list)
        individual_players = []

        for player, team in rows:
            if team is None:
                individual_players.append(player)
            else:
                groups_dict[team].append(player)

        # Creamos lista final de grupos: los grupos con team + los individuales en sublistas separadas
        input_groups = list(groups_dict.values()) + [[p] for p in individual_players]

        total_players = sum(len(g) for g in input_groups)

        if total_players < 2:
            logger.error(f"Match {match_id} tiene menos de 2 jugadores")
            raise HTTPException(status_code=400, detail="Se necesitan al menos 2 jugadores para formar equipos")

        # Validación: ningún grupo puede tener más jugadores que la mitad del total (para poder balancear)
        if any(len(group) > total_players // 2 for group in input_groups):
            logger.error(f"En match {match_id}, un grupo tiene más jugadores que el permitido por equipo")
            raise HTTPException(
                status_code=400,
                detail=f"Un grupo tiene más jugadores que el permitido por equipo (máximo {total_players // 2})"
            )

        logger.info(f"Match {match_id}: intentando balancear {total_players} jugadores en {len(input_groups)} grupos")

        # Balancear equipos usando la función
        team_a, team_b = balance_teams(input_groups)

        # Crear o actualizar equipos en la base
        if not match.team1:
            team1 = Team(name="Team 1", players=team_a)
            db.add(team1)
            db.commit()
            match.team1 = team1
        else:
            match.team1.players = team_a

        if not match.team2:
            team2 = Team(name="Team 2", players=team_b)
            db.add(team2)
            db.commit()
            match.team2 = team2
        else:
            match.team2.players = team_b

        # Actualizar MatchPlayer con la asignación del equipo
        for player in team_a:
            db.execute(
                update(MatchPlayer)
                .where(
                    MatchPlayer.match_id == match.id,
                    MatchPlayer.player_id == player.id
                )
                .values(team=TeamEnum.team1)
            )

        for player in team_b:
            db.execute(
                update(MatchPlayer)
                .where(
                    MatchPlayer.match_id == match.id,
                    MatchPlayer.player_id == player.id
                )
                .values(team=TeamEnum.team2)
            )

        db.commit()

        # Recargar match con equipos y jugadores para devolver en la respuesta
        db.refresh(match)
        match = db.query(Match).options(
            joinedload(Match.team1).joinedload(Team.players),
            joinedload(Match.team2).joinedload(Team.players)
        ).filter(Match.id == match_id).first()

        logger.info(f"Match {match_id} balanceado correctamente")

        return match

    except ValueError as e:
        logger.error(f"Error balanceando equipos para match {match_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error inesperado en balanceo de match {match_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/matches/{match_id}/balance-report", tags=["matches"], response_model=MatchReportResponse)
def match_balance_report(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).options(
        joinedload(Match.team1).joinedload(Team.players),
        joinedload(Match.team2).joinedload(Team.players)
    ).filter(Match.id == match_id).first()

    if not match:
        print(f"Match con id={match_id} no encontrado")
        logger.error(f"Match con id={match_id} no encontrado")
        raise HTTPException(status_code=404, detail="Match no encontrado")

    try:
        res = get_match_balance_report(match_id,db)
        logger.info(res)

        return res
    except Exception as e:
        logger.error(f"Error inesperado al obtener reporte: {e}")
        raise HTTPException(status_code=500, detail="Error interno al generar el reporte")


def serialize_team(team):
    return TeamResponse(
        id=team.id,
        name=team.name,
        players=[{"id": p.id, "username": p.name} for p in team.players]
    )