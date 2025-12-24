import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.player import Player
from src.schemas.player_schema import PlayerStatsUpdate
from src.services.player_service import update_player_stats
from src.utils.logger_config import test_logger as logger
from src.test.utils_common_methods import TestUtils

utils = TestUtils()

@pytest.mark.nivel("medio")
def test_stat_update_from_high_stat_evaluator(client: TestClient, db_session: Session):
    # Crear jugador promedio
    logger.info("Creando jugador promedio (player_avg)")
    utils.create_player(client, "player_avg")
    avg_player: Player = db_session.query(Player).filter_by(name="player_avg").first()
    avg_player.punteria = 50
    avg_player.velocidad = 50
    avg_player.resistencia = 50
    avg_player.defensa = 50
    avg_player.magia = 50
    avg_player.elo = 0

    # Crear jugador fuerte
    logger.info("Creando jugador fuerte (player_strong)")
    utils.create_player(client, "player_strong")
    strong_player: Player = db_session.query(Player).filter_by(name="player_strong").first()
    strong_player.punteria = 90
    strong_player.velocidad = 90
    strong_player.resistencia = 90
    strong_player.defensa = 90
    strong_player.magia = 90
    strong_player.elo = 0

    db_session.commit()

    logger.info(f"Stats iniciales de player_avg: velocidad={avg_player.velocidad}, elo={avg_player.elo}")
    logger.info(f"Stats del evaluador (player_strong): velocidad={strong_player.velocidad}, elo={strong_player.elo}")

    # Evaluación: el jugador fuerte evalúa al promedio
    stats_input = PlayerStatsUpdate(velocidad=80)
    logger.info(f"Evaluando a 'player_avg' con datos: {stats_input.dict()}")

    updated = update_player_stats(
        target_username="player_avg",
        evaluator_username="player_strong",
        stats_data=stats_input,
        db=db_session
    )

    logger.info(f"Stats después de la evaluación: velocidad={updated.velocidad}")

    assert updated.velocidad > 50, "La velocidad debería haber aumentado"
    assert updated.velocidad <= 100, "La velocidad no debe superar el límite"
