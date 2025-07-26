import random
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.models import Player, Team, Match, TeamEnum
from src.services.team_service import assign_team_players
from src.services.match_service import assign_match_winner
from src.services.player_service import get_or_create_relation, update_player_stats
from src.schemas.player_schema import PlayerStatsUpdate
from src.test.utils_common_methods import TestUtils
from typing import List, Dict, Tuple, Optional

from src.utils.logger_config import test_logger as logger
from src.main import app

utils = TestUtils()
client = TestClient(app)

STAT_NAMES = ["punteria", "velocidad", "dribbling", "defensa", "magia"]



def generate_stats_for_player(i: int) -> Dict[str, int]:
    return {
        stat: (i * factor) % 101
        for stat, factor in zip(STAT_NAMES, [11, 13, 17, 19, 23])
    }



@pytest.mark.nivel("alto")
def test_multiple_matches_with_player_evaluations(client: TestClient, db_session: Session):
    # Crear 20 jugadores humanos
    player_ids = []
    for i in range(20):
        stats = generate_stats_for_player(i)  # o generate_random_stats()
        user_id = utils.create_player(client, f"player{i}", stats=stats)
        assert user_id is not None
        #player_ids.append(user_id)

        player = db_session.query(Player).filter_by(name=f"player{i}").first()
        assert player is not None
        player_ids.append(player.id)


    num_matches = 10
    players_per_match = 10  # 5 vs 5

    for match_id in range(num_matches):
        selected_player_ids = random.sample(player_ids, players_per_match)

        # Crear match
        match_id = utils.create_match(client, players_per_match)
        match = db_session.query(Match).get(match_id)
        assert match is not None

        utils.assign_players_randomly(client, db_session, match.id, selected_player_ids)

        # Generar equipos balanceados
        res = client.post(f"/match/matches/{match.id}/generate-teams")
        assert res.status_code == 200

        db_session.refresh(match)
        assert match.team1_id is not None and match.team2_id is not None
        assert match.team1_id != match.team2_id

        team1 = db_session.query(Team).filter_by(id=match.team1_id).first()
        team2 = db_session.query(Team).filter_by(id=match.team2_id).first()

        assert len(team1.players) == (players_per_match / 2)
        assert len(team2.players) ==  (players_per_match / 2)

        # Elegir ganador aleatorio
        winning_team = random.choice([team1, team2])

        assign_match_winner(match=match, winning_team=winning_team, db=db_session)

        # --- NUEVO: simulamos evaluaciones después del partido ---
        # Por ejemplo, los 2 jugadores con mayor velocidad evalúan a otros 3 jugadores en el mismo partido

        # Obtener los jugadores con stats frescos para evaluar
        match_players = db_session.query(Player).filter(Player.id.in_(selected_player_ids)).all()


        # Ordenar por velocidad descendente para elegir evaluadores
        evaluators = sorted(match_players, key=lambda p: p.velocidad, reverse=True)[:2]

        # Para cada evaluador, elegir 3 jugadores distintos para evaluar
        for evaluator in evaluators:
            targets = [p for p in match_players if p.id != evaluator.id]
            targets_to_evaluate = random.sample(targets, k=min(3, len(targets)))
            for target in targets_to_evaluate:
                # Crear stats de evaluación: por simplicidad, el evaluador "recomienda" mejorar velocidad +5 hasta max 100
                new_velocidad = min(target.velocidad + 5, 100)
                stats_input = PlayerStatsUpdate(velocidad=new_velocidad)

                #logger.info(f"Jugador '{evaluator.name}' evalúa a '{target.name}', velocidad nueva: {new_velocidad}")

                updated = update_player_stats(
                    target_username=target.name,
                    evaluator_username=evaluator.name,
                    stats_data=stats_input,
                    db=db_session
                )

                # Aseguramos que la velocidad del target no bajó
                assert updated.velocidad >= target.velocidad

    num_matches = 6
    for match_idx in range(num_matches):
        selected_player_ids = random.sample(player_ids, players_per_match)

        # Crear match
        match_id = utils.create_match(client, players_per_match)
        match = db_session.query(Match).get(match_id)
        assert match is not None

        #utils.assign_players_to_match(client=client, match_id=match.id, player_ids=selected_player_ids)
        utils.assign_players_randomly( client, db_session, match.id, selected_player_ids)

        # Generar equipos balanceados
        res = client.post(f"/match/matches/{match.id}/generate-teams")
        assert res.status_code == 200

        db_session.refresh(match)

        reporte = client.post(f"/match/matches/{match.id}/balance-report")

        logger.info("BALANCE GENERADO DE EQUIPOS: /n", reporte.json())

        assert match.team1_id is not None and match.team2_id is not None
        assert match.team1_id != match.team2_id

        team1 = db_session.query(Team).filter_by(id=match.team1_id).first()
        team2 = db_session.query(Team).filter_by(id=match.team2_id).first()

        assert len(team1.players) == (players_per_match / 2)
        assert len(team2.players) ==  (players_per_match / 2)

        # Elegir ganador aleatorio
        winning_team = random.choice([team1, team2])

        assign_match_winner(match=match, winning_team=winning_team, db=db_session)

        # --- NUEVO: simulamos evaluaciones después del partido ---
        # Por ejemplo, los 2 jugadores con mayor velocidad evalúan a otros 3 jugadores en el mismo partido

        # Obtener los jugadores con stats frescos para evaluar
        match_players = db_session.query(Player).filter(Player.id.in_(selected_player_ids)).all()


        # Ordenar por velocidad descendente para elegir evaluadores
        evaluators = sorted(match_players, key=lambda p: p.velocidad, reverse=True)[:2]

        # Para cada evaluador, elegir 3 jugadores distintos para evaluar
        for evaluator in evaluators:
            targets = [p for p in match_players if p.id != evaluator.id]
            targets_to_evaluate = random.sample(targets, k=min(3, len(targets)))
            for target in targets_to_evaluate:
                # Crear stats de evaluación: por simplicidad, el evaluador "recomienda" mejorar velocidad +5 hasta max 100
                new_velocidad = min(target.velocidad + 5, 100)
                stats_input = PlayerStatsUpdate(velocidad=new_velocidad)

                #logger.info(f"Jugador '{evaluator.name}' evalúa a '{target.name}', velocidad nueva: {new_velocidad}")

                updated = update_player_stats(
                    target_username=target.name,
                    evaluator_username=evaluator.name,
                    stats_data=stats_input,
                    db=db_session
                )

                # Aseguramos que la velocidad del target no bajó
                assert updated.velocidad >= target.velocidad

    # Validaciones finales similares al test anterior

    players = db_session.query(Player).filter(Player.id.in_(player_ids)).all()

    multiples_partidos = [p for p in players if p.cant_partidos > 1]
    assert len(multiples_partidos) > 0, "No hay jugadores con múltiples partidos jugados"

    found_relation = False
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            relation = get_or_create_relation(players[i].id, players[j].id, db=db_session)
            if relation.games_together + relation.games_apart > 0:
                found_relation = True
                break
        if found_relation:
            break
    assert found_relation, "No se encontró relación con juegos juntos o en contra"

    # for p in players:
    #     db_session.refresh(p)
    #     logger.info(
    #         f"{p.name}: partidos={p.cant_partidos}, ganados={p.cant_partidos_ganados}, elo={p.elo}, velocidad={p.velocidad}")

