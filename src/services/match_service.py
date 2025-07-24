from typing import Optional

from sqlalchemy.orm import Session
from src.models.player import Player, PlayerRelation
from src.models.match import Match, MatchPlayer, TeamEnum
from src.models.team import Team
from fastapi import HTTPException, APIRouter
from sqlalchemy import select, insert, func

from src.services.player_service import calculate_elo, update_player_match_history, get_or_create_relation
from src.utils.balance_teams import balance_teams
from src.utils.logger_config import app_logger as logger
import random


from sqlalchemy.orm import Session
from src.schemas.match_schema import MatchCreate
from src.utils.logger_config import app_logger as logger

def create_match(match_data: MatchCreate, db: Session) -> Match:
    new_match = Match(
        date=match_data.date,
        max_players=match_data.max_players
    )

    db.add(new_match)
    db.commit()
    db.refresh(new_match)

    logger.info(f"Match creado con ID {new_match.id} y fecha {new_match.date}")
    return new_match

def assign_team_to_match(team, match, db):
    """Requisitos de la función assign_team_to_match(team, match, db):
        Validar cantidad de jugadores:
        La cantidad de jugadores en team.players debe ser menor o igual a match.max_players / 2.

        Validar que el equipo no esté ya asignado:
        No debe haber otro equipo con el mismo team.id asignado ya al match (en match.team1_id o match.team2_id).

        Validar que no haya jugadores repetidos en ambos equipos:
        Si ya hay un equipo asignado, sus jugadores no deben superponerse con los del nuevo equipo.

        Validar que los jugadores del equipo estén asignados al match:

        Obtener los jugadores ya asignados al match (tabla match_players).

        Si algún jugador del equipo no está asignado, agregarlo a la tabla, siempre que no se exceda el máximo permitido (match.max_players).

        Agregar el equipo al match:

        Si no hay equipo en team1_id, asignar ahí el nuevo equipo, o si no, asignarlo a team2_id.

        Guardar todo en la base y confirmar con commit.

        """

    max_players = match.max_players
    team_size = len(team.players)

    # 1. Validar cantidad de jugadores en el equipo
    if team_size > max_players // 2:
        raise HTTPException(
            status_code=400,
            detail=f"El equipo tiene {team_size} jugadores, que excede la mitad del máximo permitido ({max_players // 2})."
        )

    # 2. Validar que el equipo no esté ya asignado
    if match.team1_id == team.id or match.team2_id == team.id:
        raise HTTPException(status_code=400, detail="El equipo ya está asignado a este match.")

    # 3. Validar que no haya jugadores repetidos en ambos equipos
    # Obtener jugadores del equipo ya asignado si existe
    other_team_players_ids = set()
    if match.team1_id and match.team1_id != team.id:
        other_team = db.query(type(team)).get(match.team1_id)
        other_team_players_ids.update(p.id for p in other_team.players)
    if match.team2_id and match.team2_id != team.id:
        other_team = db.query(type(team)).get(match.team2_id)
        other_team_players_ids.update(p.id for p in other_team.players)

    current_team_player_ids = {p.id for p in team.players}
    overlap = current_team_player_ids.intersection(other_team_players_ids)
    if overlap:
        raise HTTPException(
            status_code=400,
            detail=f"Hay jugadores que ya están en otro equipo asignado al match: {overlap}"
        )

    # 4. Validar jugadores ya asignados al match
    assigned_player_ids = {
        row[0] for row in db.execute(
            select(MatchPlayer.player_id).where(MatchPlayer.match_id == match.id)
        )
    }

    # Cantidad actual de jugadores en el match
    current_player_count = len(assigned_player_ids)

    # Jugadores nuevos que hay que agregar al match
    new_players = [p for p in team.players if p.id not in assigned_player_ids]

    # Validar que no exceda el max_players
    if current_player_count + len(new_players) > max_players:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se pueden agregar {len(new_players)} jugadores nuevos; "
                f"excede el máximo permitido de {max_players} en el match."
            )
        )

    # 5. Asignar el equipo al match
    if not match.team1_id:
        match.team1_id = team.id
        team_enum = TeamEnum.team1
    elif not match.team2_id:
        match.team2_id = team.id
        team_enum = TeamEnum.team2
    else:
        raise HTTPException(
            status_code=400,
            detail="El match ya tiene dos equipos asignados."
        )

    # Agregar jugadores nuevos a match_players con el team correcto
    for player in new_players:
        res = assign_player_to_match(db, match,player)
        if not res:
            break

    db.commit()
    db.refresh(match)

def assign_player_to_match(db: Session, match: Match, player: Player, team: str = None) -> bool:
    # Verificar si el jugador ya está en el match
    existing = db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == match.id,
            MatchPlayer.player_id == player.id
        )
    ).first()

    if existing:
        return False  # Ya está en el match

    # Verificar si el match está lleno
    current_count = db.scalar(
        select(func.count()).select_from(MatchPlayer).where(MatchPlayer.match_id == match.id)
    )
    if current_count >= match.max_players:
        return False  # Match lleno

    # Insertar en tabla intermedia
    db.execute(
        insert(MatchPlayer).values(
            match_id=match.id,
            player_id=player.id,
            team=team
        )
    )
    db.commit()
    return True

def generate_teams_for_match(match: Match, db: Session):
    match_players = db.execute(
        select(MatchPlayer).where(MatchPlayer.match_id == match.id)
    ).scalars().all()

    if len(match_players) < 2:
        raise ValueError("No hay suficientes jugadores para formar equipos")

    existing_teams = db.execute(
        select(Team).where(Team.match_id == match.id)
    ).scalars().all()

    if len(existing_teams) >= 2:
        raise ValueError("El match ya tiene dos equipos asignados")

    players = [db.get(Player, mp.player_id) for mp in match_players]

    groups = [[p] for p in players]

    total_players = len(players)
    if any(len(group) > total_players // 2 for group in groups):
        raise ValueError("Un grupo tiene más jugadores que el permitido por equipo")

    team1, team2 = balance_teams(groups)

    # Crear equipos y asignarlos al match
    team1_entity = Team(name="Team A", players=team1, match_id=match.id)
    team2_entity = Team(name="Team B", players=team2, match_id=match.id)

    db.add_all([team1_entity, team2_entity])
    db.commit()

    # Asignar referencias en el objeto match para devolver actualizado
    match.team1 = team1_entity
    match.team2 = team2_entity

    db.refresh(match)  # Refrescar para que esté sincronizado con DB

    return match

def fill_with_bots(db: Session, match: Match) -> Match:
    current_players = match.players
    current_count = len(current_players)
    max_players = match.max_players

    # Si ya está lleno, no hacer nada
    if current_count >= max_players:
        return match

    # Calcular cuántos faltan
    missing = max_players - current_count

    # Buscar bots disponibles que no estén ya en el match
    bot_candidates = db.scalars(
        select(Player)
        .where(Player.is_bot == True)
        .where(Player.id.notin_([p.id for p in current_players]))
        .limit(missing)
    ).all()

    for bot in bot_candidates:
        match.players.append(bot)

    db.commit()
    db.refresh(match)
    return match

def assign_match_winner(match: Match, winning_team: Team, db: Session):
    # Validar que el equipo pertenece al match
    if winning_team.id not in [match.team1_id, match.team2_id]:
        raise ValueError("El equipo no pertenece al match")

    # Guardar el equipo ganador
    match.winner_team_id = winning_team.id
    db.add(match)
    db.commit()
    db.refresh(match)

    # Obtener todos los MatchPlayer
    match_players = db.query(MatchPlayer).filter_by(match_id=match.id).all()

    # Determinar equipo ganador (enum)
    winning_team_enum = TeamEnum.team1 if winning_team.id == match.team1_id else TeamEnum.team2

    # IDs de ganadores y perdedores
    winning_ids = {mp.player_id for mp in match_players if mp.team == winning_team_enum}
    losing_ids = {mp.player_id for mp in match_players if mp.team != winning_team_enum}

    # Actualizar historial de cada jugador
    for player in match.players:
        update_player_match_history(username=player.name, won=player.id in winning_ids, db=db)

    # Actualizar relaciones entre jugadores
    player_list = match.players
    for i, player1 in enumerate(player_list):
        for player2 in player_list[i + 1:]:
            same_team = (
                (player1.id in winning_ids and player2.id in winning_ids) or
                (player1.id in losing_ids and player2.id in losing_ids)
            )
            get_or_create_relation(player1.id, player2.id, db=db, new_game_together=same_team)



