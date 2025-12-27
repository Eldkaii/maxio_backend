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
    evaluated.tiro = 50
    evaluated.ritmo = 50
    evaluated.fisico = 50
    evaluated.defensa = 50
    evaluated.magia = 50
    evaluated.elo = 1300  # ELO aceptable

    # Crear evaluador con stats altas
    evaluator_name = "player_strong_progress"
    utils.create_player(client, evaluator_name)
    evaluator: Player = db_session.query(Player).filter_by(name=evaluator_name).first()
    evaluator.tiro = 90
    evaluator.ritmo = 90
    evaluator.fisico = 90
    evaluator.defensa = 90
    evaluator.magia = 90
    evaluator.elo = 1150  # ELO aceptable

    db_session.commit()

    logger.info(f"✅ Evaluado: {evaluated.name} (ritmo inicial: {evaluated.ritmo}, elo: {evaluated.elo})")
    logger.info(f"✅ Evaluador: {evaluator.name} (ritmo: {evaluator.ritmo}, elo: {evaluator.elo})")

    # Evaluar 15 veces seguidas con aumento en ritmo
    ritmoes = []
    for i in range(35):
        logger.info(f"🔁 Evaluación {i+1}/35")
        stats_input = PlayerStatsUpdate(ritmo=87)  # input positivo

        updated = update_player_stats(
            target_username=evaluated.name,
            evaluator_username=evaluator.name,
            stats_data=stats_input,
            db=db_session
        )

        ritmoes.append(updated.ritmo)
        logger.info(f"➡ ritmo después de evaluación {i+1}: {updated.ritmo}")

    # Validaciones finales
    assert all(v <= 100 for v in ritmoes), "❌ La ritmo se pasó del límite máximo (100)"
    assert ritmoes[0] > 50, "❌ La ritmo no debería mantenerse igual tras la primera evaluación"
    assert ritmoes == sorted(ritmoes), "❌ La ritmo no está aumentando progresivamente"
    logger.info("✅ Progresión de ritmo verificada correctamente")


@pytest.mark.nivel("bajo")
def test_stat_progression_up_mediocre_evaluator(client: TestClient, db_session: Session):
    logger.info("🎯 Test: Evaluación repetida para ver la progresión de stats")

    # Crear jugador evaluado con stats medias
    evaluated_name = "player_avg_progress"
    utils.create_player(client, evaluated_name)
    evaluated: Player = db_session.query(Player).filter_by(name=evaluated_name).first()
    evaluated.tiro = 50
    evaluated.ritmo = 50
    evaluated.fisico = 50
    evaluated.defensa = 50
    evaluated.magia = 50
    evaluated.elo = 1300  # ELO aceptable

    # Crear evaluador con stats altas
    evaluator_name = "player_strong_progress"
    utils.create_player(client, evaluator_name)
    evaluator: Player = db_session.query(Player).filter_by(name=evaluator_name).first()
    evaluator.tiro = 55
    evaluator.ritmo = 55
    evaluator.fisico = 55
    evaluator.defensa = 55
    evaluator.magia = 55
    evaluator.elo = 1150  # ELO aceptable

    db_session.commit()

    logger.info(f"✅ Evaluado: {evaluated.name} (ritmo inicial: {evaluated.ritmo}, elo: {evaluated.elo})")
    logger.info(f"✅ Evaluador: {evaluator.name} (ritmo: {evaluator.ritmo}, elo: {evaluator.elo})")

    # Evaluar 15 veces seguidas con aumento en ritmo
    ritmoes = []
    for i in range(35):
        logger.info(f"🔁 Evaluación {i+1}/35")
        stats_input = PlayerStatsUpdate(ritmo=87)  # input positivo

        updated = update_player_stats(
            target_username=evaluated.name,
            evaluator_username=evaluator.name,
            stats_data=stats_input,
            db=db_session
        )

        ritmoes.append(updated.ritmo)
        logger.info(f"➡ ritmo después de evaluación {i+1}: {updated.ritmo}")

    # Validaciones finales
    assert all(v <= 100 for v in ritmoes), "❌ La ritmo se pasó del límite máximo (100)"
    assert ritmoes[0] > 50, "❌ La ritmo no debería mantenerse igual tras la primera evaluación"
    assert ritmoes == sorted(ritmoes), "❌ La ritmo no está aumentando progresivamente"
    logger.info("✅ Progresión de ritmo verificada correctamente")



@pytest.mark.nivel("bajo")
def test_stat_degression_down_bad_evaluator(client: TestClient, db_session: Session):
    logger.info("🧪 Test: Evaluación negativa desde evaluador débil hacia jugador promedio")

    # Crear jugador evaluado con stats medias
    evaluated_name = "player_avg_regression"
    utils.create_player(client, evaluated_name)
    evaluated: Player = db_session.query(Player).filter_by(name=evaluated_name).first()
    evaluated.tiro = 50
    evaluated.ritmo = 50
    evaluated.fisico = 50
    evaluated.defensa = 50
    evaluated.magia = 50
    evaluated.elo = 50  # ELO aceptable

    # Crear evaluador con stats bajas
    evaluator_name = "player_weak_evaluator"
    utils.create_player(client, evaluator_name)
    evaluator: Player = db_session.query(Player).filter_by(name=evaluator_name).first()
    evaluator.tiro = 30
    evaluator.ritmo = 30
    evaluator.fisico = 30
    evaluator.defensa = 30
    evaluator.magia = 30
    evaluator.elo = 800  # ELO aceptable

    db_session.commit()

    logger.info(f"🟢 Evaluado: {evaluated.name} (ritmo inicial: {evaluated.ritmo}, elo: {evaluated.elo})")
    logger.info(f"🔴 Evaluador: {evaluator.name} (ritmo: {evaluator.ritmo}, elo: {evaluator.elo})")

    ritmoes = []

    for i in range(30):
        logger.info(f"⏬ Evaluación negativa {i+1}/30")
        stats_input = PlayerStatsUpdate(ritmo=20)

        updated = update_player_stats(
            target_username=evaluated.name,
            evaluator_username=evaluator.name,
            stats_data=stats_input,
            db=db_session
        )

        ritmoes.append(updated.ritmo)
        logger.info(f"📉 ritmo después de evaluación {i+1}: {updated.ritmo}")

    # Validaciones
    assert all(v >= 0 for v in ritmoes), "❌ La ritmo bajó por debajo de 0"
    assert ritmoes[0] < 50, "❌ No se redujo la ritmo tras la primera evaluación"
    assert ritmoes == sorted(ritmoes, reverse=True), "❌ La ritmo no está bajando progresivamente"

    logger.info("✅ Regresión de ritmo verificada correctamente")

@pytest.mark.nivel("bajo")
def test_stat_degression_down_mediocre_evaluator(client: TestClient, db_session: Session):
    logger.info("🧪 Test: Evaluación negativa desde evaluador débil hacia jugador promedio")

    # Crear jugador evaluado con stats medias
    evaluated_name = "player_avg_regression"
    utils.create_player(client, evaluated_name)
    evaluated: Player = db_session.query(Player).filter_by(name=evaluated_name).first()
    evaluated.tiro = 50
    evaluated.ritmo = 50
    evaluated.fisico = 50
    evaluated.defensa = 50
    evaluated.magia = 50
    evaluated.elo = 800  # ELO aceptable

    # Crear evaluador con stats bajas
    evaluator_name = "player_weak_evaluator"
    utils.create_player(client, evaluator_name)
    evaluator: Player = db_session.query(Player).filter_by(name=evaluator_name).first()
    evaluator.tiro = 55
    evaluator.ritmo = 55
    evaluator.fisico = 55
    evaluator.defensa = 55
    evaluator.magia = 55
    evaluator.elo = 800  # ELO aceptale

    db_session.commit()

    logger.info(f"🟢 Evaluado: {evaluated.name} (ritmo inicial: {evaluated.ritmo}, elo: {evaluated.elo})")
    logger.info(f"🔴 Evaluador: {evaluator.name} (ritmo: {evaluator.ritmo}, elo: {evaluator.elo})")

    ritmoes = []

    for i in range(30):
        logger.info(f"⏬ Evaluación negativa {i+1}/30")
        stats_input = PlayerStatsUpdate(ritmo=20)

        updated = update_player_stats(
            target_username=evaluated.name,
            evaluator_username=evaluator.name,
            stats_data=stats_input,
            db=db_session
        )

        ritmoes.append(updated.ritmo)
        logger.info(f"📉 ritmo después de evaluación {i+1}: {updated.ritmo}")

    # Validaciones
    assert all(v >= 0 for v in ritmoes), "❌ La ritmo bajó por debajo de 0"
    assert ritmoes[0] < 50, "❌ No se redujo la ritmo tras la primera evaluación"
    assert ritmoes == sorted(ritmoes, reverse=True), "❌ La ritmo no está bajando progresivamente"

    logger.info("✅ Regresión de ritmo verificada correctamente")