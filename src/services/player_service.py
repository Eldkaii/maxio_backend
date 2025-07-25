# src/services/player_service.py
from typing import Optional,Dict

from src.models.player import Player, PlayerRelation
from sqlalchemy.orm import Session
from src.models.user import User
from src.schemas.player_schema import PlayerStatsUpdate
from src.utils.logger_config import app_logger as logger
from src.utils.stat_calculator import calculate_updated_stats


def create_player_for_user(user: User, db: Session, stats: Optional[Dict[str, int]] = None, is_bot: Optional[bool] = False) -> Player:
    stats = stats or {}

    player = Player(
        name=user.username,
        cant_partidos=0,
        elo=1000,
        user_id=user.id,
        punteria=stats.get("punteria", 50),
        velocidad=stats.get("velocidad", 50),
        dribbling=stats.get("dribbling", 50),
        defensa=stats.get("defensa", 50),
        magia=stats.get("magia", 50),
        is_bot=is_bot,
    )

    # logger.info(f"Creando player: {player.name} con stats: punteria={player.punteria}, velocidad={player.velocidad}, "
    #             f"dribbling={player.dribbling}, defensa={player.defensa}, magia={player.magia}")

    db.add(player)
    db.commit()
    db.refresh(player)

    return player

def get_player_by_username(username: str, db: Session) -> Player:
    player = db.query(Player).filter(Player.name == username).first()
    if not player:
        raise ValueError(f"Player con username '{username}' no encontrado")
    logger.info(f"Player obtenido: {username}")
    return player

def add_player_relation(player1_id: int, player2_id: int, together: bool, db: Session):
    logger.info(f"Agregando {player1_id} - {player2_id}  un nuevo juego {together} juntos")
    if player1_id == player2_id:
        raise ValueError("Un jugador no puede relacionarse consigo mismo.")

    # Asegurar orden consistente para evitar duplicados (simetría)
    p1, p2 = sorted((player1_id, player2_id))

    relation = db.query(PlayerRelation).filter_by(player1_id=p1, player2_id=p2).first()
    if relation:
        if together:
            relation.games_together += 1
        else:
            relation.games_apart += 1
    else:
        if together:
            relation = PlayerRelation(
                player1_id=p1,
                player2_id=p2,
                games_together=1
            )
        else:
            relation = PlayerRelation(
                player1_id=p1,
                player2_id=p2,
                games_apart=1
            )
        db.add(relation)

    db.commit()
    db.refresh(relation)
    return relation

def update_player_stats(
    target_username: str,
    evaluator_username: str,
    stats_data: PlayerStatsUpdate,
    db: Session
) -> Player:
    # Buscar al jugador que fue evaluado
    target = db.query(Player).filter(Player.name == target_username).first()
    if not target:
        raise ValueError(f"Jugador evaluado '{target_username}' no encontrado")

    # Buscar al jugador que hizo la evaluación
    evaluator = db.query(Player).filter(Player.name == evaluator_username).first()
    if not evaluator:
        raise ValueError(f"Jugador evaluador '{evaluator_username}' no encontrado")

    current_stats = {
        "punteria": target.punteria,
        "velocidad": target.velocidad,
        "dribbling": target.dribbling,
        "defensa": target.defensa,
        "magia": target.magia,
    }

    evaluator_stats = {
        "punteria": evaluator.punteria,
        "velocidad": evaluator.velocidad,
        "dribbling": evaluator.dribbling,
        "defensa": evaluator.defensa,
        "magia": evaluator.magia,
    }

    elo = target.elo

    # Solo los stats efectivamente enviados
    incoming_stats = stats_data.dict(exclude_unset=True)

    # Calcular nuevos stats ponderados
    new_stats = calculate_updated_stats(
        current_stats=current_stats,
        evaluator_stats=evaluator_stats,
        incoming_stats=incoming_stats,
        elo=elo
    )

    for key, value in new_stats.items():
        setattr(target, key, value)

    db.commit()
    db.refresh(target)
    logger.info(f"Stats actualizados para player {target_username} (puntuado por {evaluator_username}), nuevo stat [{new_stats}]")
    return target

def calculate_elo(cant_partidos: int, cant_partidos_ganados: int, recent_results: list[bool], current_elo: int) -> int:
    # Si no ha jugado partidos, asignamos un ELO inicial
    if cant_partidos == 0:
        return 1000

    # Si tiene menos de 10 partidos, usamos un sistema más suave
    if cant_partidos < 10:
        # Valor base neutral
        base_elo = 1000
        win_rate = cant_partidos_ganados / cant_partidos
        adjustment = int((win_rate - 0.5) * 100)  # más suave que el normal
        return max(0, min(2000, base_elo + adjustment))

    # A partir de 10 partidos, se aplica la lógica completa
    win_rate = cant_partidos_ganados / cant_partidos

    streak_bonus = 0
    streak_penalty = 0

    if recent_results:
        streak_score = sum(1 if r else -1 for r in recent_results)

        if streak_score > 0:
            streak_bonus = streak_score * 5
        elif streak_score < 0:
            streak_penalty = abs(streak_score) * 7

    base_change = int((win_rate - 0.5) * 200)
    new_elo = current_elo + base_change + streak_bonus - streak_penalty

    return max(0, min(2000, new_elo))

def update_player_match_history(username: str, won: bool, db: Session):
    player = db.query(Player).filter_by(name=username).first()
    if not player:
        raise ValueError(f"Player with username '{username}' not found")

    # Actualizar historial de partidos
    player.cant_partidos += 1
    if won:
        player.cant_partidos_ganados += 1

    # Actualizar resultados recientes (máximo 10)
    if player.recent_results is None:
        player.recent_results = []
    player.recent_results = (player.recent_results or []) + [won]
    player.recent_results = player.recent_results[-10:]

    # Recalcular ELO
    player.elo = calculate_elo(
        cant_partidos=player.cant_partidos,
        cant_partidos_ganados=player.cant_partidos_ganados,
        recent_results=player.recent_results,
        current_elo=player.elo,
    )

    db.commit()

def get_or_create_relation(
    player1_id: int,
    player2_id: int,
    db: Session,
    new_game_together: Optional[bool] = None
) -> PlayerRelation:
    # Ordenar para evitar duplicados cruzados
    p1, p2 = sorted([player1_id, player2_id])
    relation = db.query(PlayerRelation).filter_by(player1_id=p1, player2_id=p2).first()

    if not relation:
        relation = PlayerRelation(player1_id=p1, player2_id=p2, games_together=0, games_apart=0)
        db.add(relation)

    # Si se indica actualización, actualizar contador y guardar
    if new_game_together is not None:
        if new_game_together:
            relation.games_together += 1
        else:
            relation.games_apart += 1


        db.commit()
        db.refresh(relation)

    return relation






