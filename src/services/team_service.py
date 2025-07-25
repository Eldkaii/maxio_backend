from typing import List, Optional, Set
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from src.models import MatchPlayer, TeamEnum
from src.models.player import Player, PlayerRelation
from src.models.team import Team
from typing import List, Tuple, Dict
from src.utils.logger_config import app_logger as logger


def assign_team_players(
    db: Session,
    team_id: int,
    player_ids: Optional[List[int]] = None,
    player_usernames: Optional[List[str]] = None
) -> Team:
    from sqlalchemy.orm import joinedload
    from sqlalchemy import select

    # Obtener el equipo con jugadores cargados
    result = db.execute(
        select(Team).options(joinedload(Team.players)).where(Team.id == team_id)
    ).unique().one()
    team = result[0]

    # Sets para IDs y nombres (para evitar duplicados ya aquí)
    player_ids = set(player_ids or [])
    player_usernames = set(player_usernames or [])

    # Traer IDs de jugadores por usernames
    players_from_usernames = db.execute(
        select(Player.id).where(Player.name.in_(player_usernames))
    ).scalars().all()
    #logger.info("players_from_usernames", players_from_usernames)

    # Unir todos los IDs, eliminando duplicados
    all_player_ids = player_ids.union(set(players_from_usernames))
    logger.info(f"players_from_id: {all_player_ids}")

    # Traer ahora TODOS los jugadores únicos solo UNA vez
    unique_players = db.execute(
        select(Player).where(Player.id.in_(all_player_ids))
    ).scalars().all()


    # Reemplazamos la colección de jugadores asignados al equipo
    team.players[:] = unique_players

    db.commit()
    db.refresh(team)

    return team


def get_players_by_team_enum(match_id: int, team_enum: TeamEnum, db: Session) -> List[Player]:
    """
    Devuelve los jugadores de un equipo dentro de un match, usando TeamEnum.
    """
    match_players = (
        db.query(MatchPlayer)
        .filter(MatchPlayer.match_id == match_id, MatchPlayer.team == team_enum)
        .all()
    )
    player_ids = [mp.player_id for mp in match_players]

    players = db.query(Player).filter(Player.id.in_(player_ids)).all()

    logger.info(f"Players en {team_enum} del match {match_id}: {[p.name for p in players]}")

    return players


def get_team_relations(players: List[Player], db: Session) -> Dict[str, List[Tuple[str, str, int]]]:
    """
    Retorna un resumen de las relaciones entre los jugadores del equipo:
    - 'together': cuántas veces jugaron juntos
    - 'apart': cuántas veces jugaron en contra
    """
    relations_together = []
    relations_apart = []

    player_ids = [p.id for p in players]
    player_lookup = {p.id: p.name for p in players}

    for i in range(len(player_ids)):
        for j in range(i + 1, len(player_ids)):
            id1 = player_ids[i]
            id2 = player_ids[j]

            relation = (
                db.query(PlayerRelation)
                .filter(
                    ((PlayerRelation.player1_id == id1) & (PlayerRelation.player2_id == id2)) |
                    ((PlayerRelation.player1_id == id2) & (PlayerRelation.player2_id == id1))
                )
                .first()
            )

            if not relation:
                continue  # No hay relación previa

            name1 = player_lookup[id1]
            name2 = player_lookup[id2]

            if relation.games_together > 0:
                relations_together.append((name1, name2, relation.games_together))

            if relation.games_apart > 0:
                relations_apart.append((name1, name2, relation.games_apart))

    return {
        "together": relations_together,
        "apart": relations_apart
    }
