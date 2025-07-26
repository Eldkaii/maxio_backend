from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from src.models.player import Player, PlayerRelation
from src.models.match import Match, MatchPlayer, TeamEnum
from src.models.team import Team
from fastapi import HTTPException, APIRouter
from sqlalchemy import select, insert, func
from typing import List, Tuple
from sqlalchemy import select, update

from src.services.player_service import calculate_elo, update_player_match_history, get_or_create_relation
from src.services.team_service import get_team_relations, get_players_by_team_enum
from src.utils.balance_teams import balance_teams, chemistry_score, team_stats_summary, STAT_NAMES, \
    calculate_balance_score, calculate_stat_diff
from src.utils.build_match_response import build_individual_stats
from src.utils.logger_config import app_logger as logger
import random


from sqlalchemy.orm import Session
from src.schemas.match_schema import MatchCreate, MatchReportResponse, TeamBalanceReport
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
        res = assign_player_to_match(db, match,player,team_enum)
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

# def generate_teams_for_match(match: Match, db: Session):
#     match_players = db.execute(
#         select(MatchPlayer).where(MatchPlayer.match_id == match.id)
#     ).scalars().all()
#
#     if len(match_players) < 2:
#         raise ValueError("No hay suficientes jugadores para formar equipos")
#
#     existing_teams = db.execute(
#         select(Team).where(Team.match_id == match.id)
#     ).scalars().all()
#
#
#
#     if len(existing_teams) >= 2:
#         raise ValueError("El match ya tiene dos equipos asignados")
#
#     players = [db.get(Player, mp.player_id) for mp in match_players]
#
#     groups = [[p] for p in players]
#
#
#     total_players = len(players)
#     if any(len(group) > total_players // 2 for group in groups):
#         raise ValueError("Un grupo tiene más jugadores que el permitido por equipo")
#
#     set_player_groups_for_match(match, groups,db)
#     team1, team2 = balance_teams(groups)
#
#     # Crear equipos y asignarlos al match
#     team1_entity = Team(name="Team A", players=team1, match_id=match.id)
#     team2_entity = Team(name="Team B", players=team2, match_id=match.id)
#
#     db.add_all([team1_entity, team2_entity])
#     db.commit()
#
#     # Asignar referencias en el objeto match para devolver actualizado
#     match.team1 = team1_entity
#     match.team2 = team2_entity
#
#     db.refresh(match)  # Refrescar para que esté sincronizado con DB
#
#     return match

def generate_teams_for_match(match_id: int, db: Session) -> Match:
    match = db.query(Match).options(
        joinedload(Match.team1).joinedload(Team.players),
        joinedload(Match.team2).joinedload(Team.players)
    ).filter(Match.id == match_id).first()

    if not match:
        logger.error(f"Match con id={match_id} no encontrado")
        raise HTTPException(status_code=404, detail="Match no encontrado")

    rows = db.execute(
        select(Player, MatchPlayer.team)
        .join(MatchPlayer, MatchPlayer.player_id == Player.id)
        .where(MatchPlayer.match_id == match.id)
    ).all()

    # logger.info(f"Total rows obtenidas del match {match.id}: {len(rows)}")
    # for i, (player, team) in enumerate(rows):
    #     logger.info(f"Row {i + 1}: Player(id={player.id}, name={player.name}), team={team}")

    if not rows:
        logger.warning(f"No hay jugadores asignados al match {match_id}")
        raise HTTPException(status_code=400, detail="No hay jugadores asignados al match")

    groups_dict = defaultdict(list)
    individual_players = []

    for player, team in rows:
        if team is None:
            #logger.info(f"Jugador sin team: {player.name} (id={player.id}) → agregado a individual_players")
            individual_players.append(player)
        else:
            #logger.info(f"Jugador con team '{team}': {player.name} (id={player.id}) → agregado a groups_dict[{team}]")
            groups_dict[team].append(player)

    input_groups = list(groups_dict.values()) + [[p] for p in individual_players]

    # Loguear cómo quedaron los grupos armados
    # logger.info(f"Total de grupos prearmados (con team): {len(groups_dict)}")
    # for team_key, group in groups_dict.items():
    #     nombres = [p.name for p in group]
    #     logger.info(f"Grupo del team {team_key}: {nombres}")
    #
    # logger.info(f"Total de jugadores individuales: {len(individual_players)}")
    # logger.info(f"input_groups final: {[[p.name for p in g] for g in input_groups]}")

    set_pre_set_player_groups_for_match(match, input_groups,db)

    total_players = sum(len(g) for g in input_groups)

    if total_players < 2:
        logger.error(f"Match {match_id} tiene menos de 2 jugadores")
        raise HTTPException(status_code=400, detail="Se necesitan al menos 2 jugadores para formar equipos")

    if any(len(group) > total_players // 2 for group in input_groups):
        logger.error(f"En match {match_id}, un grupo tiene más jugadores que el permitido por equipo")
        raise HTTPException(
            status_code=400,
            detail=f"Un grupo tiene más jugadores que el permitido por equipo (máximo {total_players // 2})"
        )

    logger.info(f"Match {match_id}: intentando balancear {total_players} jugadores con {len(groups_dict)} grupos")

    team_a, team_b = balance_teams(input_groups)

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

    db.refresh(match)
    match = db.query(Match).options(
        joinedload(Match.team1).joinedload(Team.players),
        joinedload(Match.team2).joinedload(Team.players)
    ).filter(Match.id == match_id).first()

    logger.info(f"Match {match_id} balanceado correctamente")
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

def get_match_balance_report(match_id: int, db: Session) -> MatchReportResponse:
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise ValueError("Match no encontrado")

    # Obtener jugadores por equipo
    team1_players: list[Player] = get_players_by_team_enum(match_id, TeamEnum.team1, db)
    team2_players: list[Player] = get_players_by_team_enum(match_id, TeamEnum.team2, db)

    # Calcular stats agregadas por equipo
    team1_total = team_stats_summary(team1_players)
    team2_total = team_stats_summary(team2_players)

    #print("match.pre_set_groups:", match.pre_set_groups)

    players_preserved_groups , names_players_preserved_groups = get_player_groups_from_match(match,db)


    # Crear objetos de respuesta por equipo
    team1_report = TeamBalanceReport(
        players=[p.name for p in team1_players],
        total_stats=team1_total,
        individual_stats=build_individual_stats(team1_players),
        chemistry_score=chemistry_score(team1_players),
    )

    team2_report = TeamBalanceReport(
        players=[p.name for p in team2_players],
        total_stats=team2_total,
        individual_stats=build_individual_stats(team2_players),
        chemistry_score=chemistry_score(team2_players),
    )

    # Ensamblar la respuesta completa
    response = MatchReportResponse(
        match_id=match_id,
        teams={
            "team_1": team1_report,
            "team_2": team2_report,
        },
        preserved_groups=names_players_preserved_groups,
        balance_score=calculate_balance_score(team1_players, team2_players),
        stat_diff=calculate_stat_diff(team1_players, team2_players),
        relations_summary={
            "team_1": get_team_relations(team1_players, db),
            "team_2": get_team_relations(team2_players, db),
        },
    )

    return response


def get_player_groups_from_match(match: Match, db: Session) -> Tuple[List[List[Player]], List[List[str]]]:
    """
    Devuelve:
    - Una lista de listas de objetos Player que representan los grupos predefinidos.
    - Una lista de listas de nombres de esos jugadores (en el mismo orden).
    """
    player_groups = []
    player_name_groups = []

    for group_ids in match.pre_set_groups or []:
        if len(group_ids) <= 1:
            continue  # Ignorar grupos de un solo jugador

        players = db.query(Player).filter(Player.id.in_(group_ids)).all()
        players_dict = {p.id: p for p in players}

        ordered_group = [players_dict[pid] for pid in group_ids if pid in players_dict]


        player_groups.append(ordered_group)
        name_group = [p.name for p in ordered_group]
        player_name_groups.append(name_group)

    return player_groups, player_name_groups

def set_pre_set_player_groups_for_match(match: Match, groups: List[List[Player]], db: Session) -> None:
    """
    Recibe una lista de grupos de Player y actualiza el campo pre_set_groups con sus IDs.
    """
    match.pre_set_groups = [[player.id for player in group] for group in groups]
    db.add(match)
    db.commit()