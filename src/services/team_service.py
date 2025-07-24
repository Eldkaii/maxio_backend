from typing import List, Optional, Set
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from src.models.player import Player
from src.models.team import Team


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
    print("players_from_usernames", players_from_usernames)

    # Unir todos los IDs, eliminando duplicados
    all_player_ids = player_ids.union(set(players_from_usernames))
    print("players_from_id", all_player_ids)

    # Traer ahora TODOS los jugadores únicos solo UNA vez
    unique_players = db.execute(
        select(Player).where(Player.id.in_(all_player_ids))
    ).scalars().all()

    for player in unique_players:
        print("unique_players", player.id)

    # Reemplazamos la colección de jugadores asignados al equipo
    team.players[:] = unique_players

    db.commit()
    db.refresh(team)

    return team