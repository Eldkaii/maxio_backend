import pytest
from sqlalchemy.orm import Session
from src.models import Player
from src.services.match_service import assign_match_winner
from src.test.utils_common_methods import TestUtils


@pytest.fixture
def setup_match_teams_players(client, db_session: Session):
    utils = TestUtils()
    # Usamos el método común que ya hace todo lo necesario
    return utils.setup_match_teams_players(client, db_session)


# def test_assign_match_winner(db_session: Session, setup_match_teams_players):
#     match, team1, team2, players_team1, players_team2 = setup_match_teams_players
#
#     # Ejecutar asignación de ganador
#     assign_match_winner(match=match, winning_team=team1, db=db_session)
#
#     # Refrescar match y verificar ganador
#     db_session.refresh(match)
#     assert match.winner_team_id == team1.id
#
#     # Verificar estadísticas actualizadas para ganadores
#     for player in players_team1:
#         db_session.refresh(player)
#         assert player.cant_partidos == 6
#         assert player.cant_partidos_ganados == 4
#         assert len(player.recent_results) <= 10
#         assert player.recent_results[-1] is True
#
#     # Verificar estadísticas actualizadas para perdedores
#     for player in players_team2:
#         db_session.refresh(player)
#         assert player.cant_partidos == 6
#         assert player.cant_partidos_ganados == 2
#         assert len(player.recent_results) <= 10
#         assert player.recent_results[-1] is False
