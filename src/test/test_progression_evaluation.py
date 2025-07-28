import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.player import Player
from src.schemas.player_schema import PlayerStatsUpdate
from src.services.player_service import update_player_stats
from src.test.utils_common_methods import TestUtils
from src.utils.logger_config import test_logger as logger

utils = TestUtils()


@pytest.mark.nivel("bajo")
def test_stat_progression_up_high_evaluator(client: TestClient, db_session: Session):
    logger.info("🎯 Test: Evaluación repetida para ver la progresión de stats")

    # Crear jugador evaluado con stats medias
    evaluated_name = "player_avg_progress"
    utils.create_player(client, evaluated_name)
    evaluated: Player = db_session.query(Player).filter_by(name=evaluated_name).first()
    evaluated.punteria = 50
    evaluated.velocidad = 50
    evaluated.dribbling = 50
    evaluated.defensa = 50
    evaluated.magia = 50
    evaluated.elo = 1300  # ELO aceptable

    # Crear evaluador con stats altas
    evaluator_name = "player_strong_progress"
    utils.create_player(client, evaluator_name)
    evaluator: Player = db_session.query(Player).filter_by(name=evaluator_name).first()
    evaluator.punteria = 90
    evaluator.velocidad = 90
    evaluator.dribbling = 90
    evaluator.defensa = 90
    evaluator.magia = 90
    evaluator.elo = 1150  # ELO aceptable

    db_session.commit()

    logger.info(f"✅ Evaluado: {evaluated.name} (velocidad inicial: {evaluated.velocidad}, elo: {evaluated.elo})")
    logger.info(f"✅ Evaluador: {evaluator.name} (velocidad: {evaluator.velocidad}, elo: {evaluator.elo})")

    # Evaluar 15 veces seguidas con aumento en velocidad
    velocidades = []
    for i in range(35):
        logger.info(f"🔁 Evaluación {i+1}/35")
        stats_input = PlayerStatsUpdate(velocidad=87)  # input positivo

        updated = update_player_stats(
            target_username=evaluated.name,
            evaluator_username=evaluator.name,
            stats_data=stats_input,
            db=db_session
        )

        velocidades.append(updated.velocidad)
        logger.info(f"➡ Velocidad después de evaluación {i+1}: {updated.velocidad}")

    # Validaciones finales
    assert all(v <= 100 for v in velocidades), "❌ La velocidad se pasó del límite máximo (100)"
    assert velocidades[0] > 50, "❌ La velocidad no debería mantenerse igual tras la primera evaluación"
    assert velocidades == sorted(velocidades), "❌ La velocidad no está aumentando progresivamente"
    logger.info("✅ Progresión de velocidad verificada correctamente")


@pytest.mark.nivel("bajo")
def test_stat_progression_up_mediocre_evaluator(client: TestClient, db_session: Session):
    logger.info("🎯 Test: Evaluación repetida para ver la progresión de stats")

    # Crear jugador evaluado con stats medias
    evaluated_name = "player_avg_progress"
    utils.create_player(client, evaluated_name)
    evaluated: Player = db_session.query(Player).filter_by(name=evaluated_name).first()
    evaluated.punteria = 50
    evaluated.velocidad = 50
    evaluated.dribbling = 50
    evaluated.defensa = 50
    evaluated.magia = 50
    evaluated.elo = 1300  # ELO aceptable

    # Crear evaluador con stats altas
    evaluator_name = "player_strong_progress"
    utils.create_player(client, evaluator_name)
    evaluator: Player = db_session.query(Player).filter_by(name=evaluator_name).first()
    evaluator.punteria = 55
    evaluator.velocidad = 55
    evaluator.dribbling = 55
    evaluator.defensa = 55
    evaluator.magia = 55
    evaluator.elo = 1150  # ELO aceptable

    db_session.commit()

    logger.info(f"✅ Evaluado: {evaluated.name} (velocidad inicial: {evaluated.velocidad}, elo: {evaluated.elo})")
    logger.info(f"✅ Evaluador: {evaluator.name} (velocidad: {evaluator.velocidad}, elo: {evaluator.elo})")

    # Evaluar 15 veces seguidas con aumento en velocidad
    velocidades = []
    for i in range(35):
        logger.info(f"🔁 Evaluación {i+1}/35")
        stats_input = PlayerStatsUpdate(velocidad=87)  # input positivo

        updated = update_player_stats(
            target_username=evaluated.name,
            evaluator_username=evaluator.name,
            stats_data=stats_input,
            db=db_session
        )

        velocidades.append(updated.velocidad)
        logger.info(f"➡ Velocidad después de evaluación {i+1}: {updated.velocidad}")

    # Validaciones finales
    assert all(v <= 100 for v in velocidades), "❌ La velocidad se pasó del límite máximo (100)"
    assert velocidades[0] > 50, "❌ La velocidad no debería mantenerse igual tras la primera evaluación"
    assert velocidades == sorted(velocidades), "❌ La velocidad no está aumentando progresivamente"
    logger.info("✅ Progresión de velocidad verificada correctamente")



@pytest.mark.nivel("bajo")
def test_stat_degression_down_bad_evaluator(client: TestClient, db_session: Session):
    logger.info("🧪 Test: Evaluación negativa desde evaluador débil hacia jugador promedio")

    # Crear jugador evaluado con stats medias
    evaluated_name = "player_avg_regression"
    utils.create_player(client, evaluated_name)
    evaluated: Player = db_session.query(Player).filter_by(name=evaluated_name).first()
    evaluated.punteria = 50
    evaluated.velocidad = 50
    evaluated.dribbling = 50
    evaluated.defensa = 50
    evaluated.magia = 50
    evaluated.elo = 50  # ELO aceptable

    # Crear evaluador con stats bajas
    evaluator_name = "player_weak_evaluator"
    utils.create_player(client, evaluator_name)
    evaluator: Player = db_session.query(Player).filter_by(name=evaluator_name).first()
    evaluator.punteria = 30
    evaluator.velocidad = 30
    evaluator.dribbling = 30
    evaluator.defensa = 30
    evaluator.magia = 30
    evaluator.elo = 800  # ELO aceptable

    db_session.commit()

    logger.info(f"🟢 Evaluado: {evaluated.name} (velocidad inicial: {evaluated.velocidad}, elo: {evaluated.elo})")
    logger.info(f"🔴 Evaluador: {evaluator.name} (velocidad: {evaluator.velocidad}, elo: {evaluator.elo})")

    velocidades = []

    for i in range(30):
        logger.info(f"⏬ Evaluación negativa {i+1}/30")
        stats_input = PlayerStatsUpdate(velocidad=20)

        updated = update_player_stats(
            target_username=evaluated.name,
            evaluator_username=evaluator.name,
            stats_data=stats_input,
            db=db_session
        )

        velocidades.append(updated.velocidad)
        logger.info(f"📉 Velocidad después de evaluación {i+1}: {updated.velocidad}")

    # Validaciones
    assert all(v >= 0 for v in velocidades), "❌ La velocidad bajó por debajo de 0"
    assert velocidades[0] < 50, "❌ No se redujo la velocidad tras la primera evaluación"
    assert velocidades == sorted(velocidades, reverse=True), "❌ La velocidad no está bajando progresivamente"

    logger.info("✅ Regresión de velocidad verificada correctamente")

@pytest.mark.nivel("bajo")
def test_stat_degression_down_mediocre_evaluator(client: TestClient, db_session: Session):
    logger.info("🧪 Test: Evaluación negativa desde evaluador débil hacia jugador promedio")

    # Crear jugador evaluado con stats medias
    evaluated_name = "player_avg_regression"
    utils.create_player(client, evaluated_name)
    evaluated: Player = db_session.query(Player).filter_by(name=evaluated_name).first()
    evaluated.punteria = 50
    evaluated.velocidad = 50
    evaluated.dribbling = 50
    evaluated.defensa = 50
    evaluated.magia = 50
    evaluated.elo = 800  # ELO aceptable

    # Crear evaluador con stats bajas
    evaluator_name = "player_weak_evaluator"
    utils.create_player(client, evaluator_name)
    evaluator: Player = db_session.query(Player).filter_by(name=evaluator_name).first()
    evaluator.punteria = 55
    evaluator.velocidad = 55
    evaluator.dribbling = 55
    evaluator.defensa = 55
    evaluator.magia = 55
    evaluator.elo = 800  # ELO aceptale

    db_session.commit()

    logger.info(f"🟢 Evaluado: {evaluated.name} (velocidad inicial: {evaluated.velocidad}, elo: {evaluated.elo})")
    logger.info(f"🔴 Evaluador: {evaluator.name} (velocidad: {evaluator.velocidad}, elo: {evaluator.elo})")

    velocidades = []

    for i in range(30):
        logger.info(f"⏬ Evaluación negativa {i+1}/30")
        stats_input = PlayerStatsUpdate(velocidad=20)

        updated = update_player_stats(
            target_username=evaluated.name,
            evaluator_username=evaluator.name,
            stats_data=stats_input,
            db=db_session
        )

        velocidades.append(updated.velocidad)
        logger.info(f"📉 Velocidad después de evaluación {i+1}: {updated.velocidad}")

    # Validaciones
    assert all(v >= 0 for v in velocidades), "❌ La velocidad bajó por debajo de 0"
    assert velocidades[0] < 50, "❌ No se redujo la velocidad tras la primera evaluación"
    assert velocidades == sorted(velocidades, reverse=True), "❌ La velocidad no está bajando progresivamente"

    logger.info("✅ Regresión de velocidad verificada correctamente")