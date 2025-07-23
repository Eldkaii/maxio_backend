# src/test/test_player_relation.py

import pytest
from sqlalchemy.orm import Session
from src.models.player import PlayerRelation, Player
from src.services.player_service import add_player_relation
from src.test.utils_common_methods import TestUtils

utils = TestUtils()

@pytest.mark.nivel("bajo")
def test_create_and_update_player_relation(client, db_session: Session):
    # Crear dos jugadores
    player1_id = utils.create_player(client, "rel_A")
    player2_id = utils.create_player(client, "rel_B")

    # Verificar que ambos jugadores existen
    player1 = db_session.query(Player).get(player1_id)
    player2 = db_session.query(Player).get(player2_id)
    assert player1 and player2, "Ambos jugadores deben existir en la base de datos"

    # Crear relación: jugaron juntos
    relation = add_player_relation(player1.id, player2.id, together=True, db=db_session)
    assert relation.games_together == 1
    assert relation.games_apart == 0

    # Actualizar relación: ahora jugaron separados
    relation = add_player_relation(player1.id, player2.id, together=False, db=db_session)
    assert relation.games_together == 1
    assert relation.games_apart == 1

    # Verificar que no existe duplicado en orden inverso
    reverse = db_session.query(PlayerRelation).filter_by(
        player1_id=player2.id, player2_id=player1.id
    ).first()
    assert reverse is None, "No debe haber duplicados en la dirección inversa"
