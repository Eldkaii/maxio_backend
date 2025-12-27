# src/test/test_update_player_match_history.py
import uuid

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from src.models.player import Player
from src.services.player_service import update_player_match_history
from src.test.utils_common_methods import TestUtils

utils = TestUtils()


@pytest.fixture(scope="function")
def setup_player(client: TestClient, db_session: Session) -> Player:
    username = f"testplayer_{uuid.uuid4().hex[:8]}"  # genera nombre único

    # Asegurar que no exista
    existing = db_session.query(Player).filter_by(name=username).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    # Crear player desde la API
    utils.create_player(client, username)

    # Modificar campos directamente
    player = db_session.query(Player).filter_by(name=username).first()
    player.cant_partidos = 5
    player.cant_partidos_ganados = 3
    player.recent_results = [True, False, True]
    player.elo = 1000
    db_session.commit()

    return player

@pytest.mark.nivel("medio")
def test_update_player_match_history_win(db_session: Session, setup_player: Player):
    update_player_match_history(username=setup_player.name, won=True, db=db_session)

    db_session.refresh(setup_player)
    assert setup_player.cant_partidos == 6
    assert setup_player.cant_partidos_ganados == 4
    assert setup_player.recent_results[-1] is True
    assert len(setup_player.recent_results) == 4
    assert isinstance(setup_player.elo, int)


@pytest.mark.nivel("medio")
def test_update_player_match_history_loss(db_session: Session, setup_player: Player):
    update_player_match_history(username=setup_player.name, won=False, db=db_session)

    db_session.refresh(setup_player)
    assert setup_player.cant_partidos == 6
    assert setup_player.cant_partidos_ganados == 3  # no cambia
    assert setup_player.recent_results[-1] is False
    assert len(setup_player.recent_results) == 4
    assert isinstance(setup_player.elo, int)

@pytest.mark.nivel("medio")
def test_elo_max_limit(client: TestClient, db_session: Session):
    username = "elo_max"
    utils.create_player(client, username)

    player = db_session.query(Player).filter_by(name=username).first()
    player.cant_partidos = 50
    player.cant_partidos_ganados = 50
    player.recent_results = [True] * 10
    player.elo = 1995
    db_session.commit()

    update_player_match_history(username=username, won=True, db=db_session)
    db_session.refresh(player)

    assert player.elo <= 2000

@pytest.mark.nivel("medio")
def test_elo_min_limit(client: TestClient, db_session: Session):
    username = "elo_min"
    utils.create_player(client, username)

    player = db_session.query(Player).filter_by(name=username).first()
    player.cant_partidos = 50
    player.cant_partidos_ganados = 0
    player.recent_results = [False] * 10
    player.elo = 5
    db_session.commit()

    update_player_match_history(username=username, won=False, db=db_session)
    db_session.refresh(player)

    assert player.elo >= 0


@pytest.mark.nivel("medio")
def test_elo_updated_on_win(client: TestClient, db_session: Session):
    username = "elo_win"
    utils.create_player(client, username)

    player = db_session.query(Player).filter_by(name=username).first()
    player.cant_partidos = 10
    player.cant_partidos_ganados = 5
    player.recent_results = [True] * 5 + [False] * 5
    player.elo = 1000
    db_session.commit()

    update_player_match_history(username=username, won=True, db=db_session)
    db_session.refresh(player)

    assert player.elo != 1000


@pytest.mark.nivel("medio")
def test_update_when_recent_results_is_none(client: TestClient, db_session: Session):
    username = "null_recent"
    utils.create_player(client, username)

    player = db_session.query(Player).filter_by(name=username).first()
    player.cant_partidos = 2
    player.cant_partidos_ganados = 1
    player.recent_results = None
    player.elo = 1000
    db_session.commit()

    update_player_match_history(username=username, won=False, db=db_session)
    db_session.refresh(player)

    assert isinstance(player.recent_results, list)
    assert player.recent_results[-1] is False


@pytest.mark.nivel("medio")
def test_recent_results_max_length(client: TestClient, db_session: Session):
    username = "recent_max"
    utils.create_player(client, username)

    player = db_session.query(Player).filter_by(name=username).first()
    player.cant_partidos = 20
    player.cant_partidos_ganados = 10
    player.recent_results = [True, False] * 5  # 10 resultados
    player.elo = 1000
    db_session.commit()

    update_player_match_history(username=username, won=True, db=db_session)
    db_session.refresh(player)

    assert len(player.recent_results) == 10
    assert player.recent_results[-1] is True


@pytest.mark.nivel("medio")
def test_update_player_match_history_invalid_user(db_session: Session):
    with pytest.raises(ValueError, match="Player with username 'unknown_user' not found"):
        update_player_match_history(username="unknown_user", won=True, db=db_session)
