import pytest
from fastapi.testclient import TestClient

from src.models import Player
from src.models.player import PlayerRelation
from sqlalchemy.orm import Session

from src.services.player_service import get_or_create_relation
from src.test.utils_common_methods import TestUtils

utils = TestUtils()

@pytest.fixture
def seed_players_and_relations(client: TestClient, db_session: Session):
    # Crear jugadores
    usernames = ["Alice", "Bob", "Charlie"]
    utils.create_players(client, usernames)
    utils.create_player(client, "Bot1",True)
    utils.create_player(client, "Bot2", True)

    # Crear relaciones con contador adecuado
    # Primero necesitamos obtener los player_ids para los usernames
    usernames = ["Alice", "Bob", "Charlie","Bot1","Bot2"]
    player_ids = {}
    for username in usernames:
        player = utils.get_player(client, username)
        player_ids[username] = player["id"]

    # Función para crear la relación y sumar games_together o games_apart múltiples veces
    def add_relation(p1: str, p2: str, games_together: int = 0, games_apart: int = 0):
        # Usamos player IDs ordenados en get_or_create_relation
        id1 = player_ids[p1]
        id2 = player_ids[p2]

        # Crear relación sin actualizar contadores para asegurarnos que existe
        get_or_create_relation(id1, id2, db_session)

        # Incrementar games_together el número de veces necesario
        for _ in range(games_together):
            get_or_create_relation(id1, id2, db_session, new_game_together=True)

        # Incrementar games_apart el número de veces necesario
        for _ in range(games_apart):
            get_or_create_relation(id1, id2, db_session, new_game_together=False)

    add_relation("Alice", "Bob", games_together=5)
    add_relation("Alice", "Charlie", games_apart=3)
    add_relation("Alice", "Bot1", games_together=7)
    add_relation("Alice", "Bot2", games_apart=2)

    yield

@pytest.mark.nivel("medio")
def test_top_teammates_success(client: TestClient, seed_players_and_relations):
    res = client.get("/player/Alice/top_teammates")
    assert res.status_code == 200
    data = res.json()

    assert any(d["name"] == "Bob" for d in data)
    assert any(d["name"] == "Bot1" for d in data)
    assert all("games" in d for d in data)


@pytest.mark.nivel("medio")
def test_top_allies_with_limit(client: TestClient, seed_players_and_relations):
    res = client.get("/player/Alice/top_allies?limit=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1


@pytest.mark.nivel("medio")
def test_top_opponents_exclude_bots(client: TestClient, seed_players_and_relations):
    res = client.get("/player/Alice/top_opponents?exclude_bots=true")
    assert res.status_code == 200
    data = res.json()
    assert all("Bot" not in d["name"] for d in data)


@pytest.mark.nivel("medio")
def test_top_allies_not_found(client: TestClient):
    res = client.get("/player/NoExiste/top_allies")
    assert res.status_code == 404
    assert res.json()["detail"] == "Player con username 'NoExiste' no encontrado"
