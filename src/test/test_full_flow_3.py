import random
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict

from src.models import Player, Team, Match
from src.models.notification import Notification
from src.models.match_result_reply import MatchResultReply
from src.schemas.player_schema import PlayerStatsUpdate
from src.services.player_service import get_or_create_relation, update_player_stats
from src.notification.notification_dispatcher import dispatch_pending_notifications
from src.test.utils_common_methods import TestUtils
from src.utils.logger_config import test_logger as logger
from src.main import app

utils = TestUtils()
client = TestClient(app)

STAT_NAMES = ["tiro", "ritmo", "fisico", "defensa", "aura"]


def generate_stats_for_player(i: int) -> Dict[str, int]:
    return {
        stat: (i * factor) % 101
        for stat, factor in zip(STAT_NAMES, [11, 13, 17, 19, 23])
    }

@pytest.mark.nivel("medio")
def test_match_closes_by_majority_votes(
    client: TestClient,
    db_session: Session
):
    match, team1, team2 = utils.create_balanced_match(
        client, db_session, players_per_team=5
    )

    # ─────────────────────────────
    # Crear notificaciones reales
    # ─────────────────────────────
    for player in team1.players + team2.players:
        db_session.add(
            Notification(
                user_id=player.user.id,
                event_type="MATCH_RESULT",
                channel="telegram",
                status="pending",
                available_at=datetime.utcnow() - timedelta(seconds=1),
                payload={
                    "match_id": match.id,
                    "team1_id": team1.id,
                    "team2_id": team2.id,
                }
            )
        )
    db_session.commit()

    # ─────────────────────────────
    # Forzar resultado irreversible
    # team1: 6 votos win
    # team2: 3 votos loss
    # ─────────────────────────────
    voters_team1 = team1.players + team2.players[:1]  # 6 jugadores
    voters_team2 = team2.players[1:4]                  # 3 jugadores

    for player in voters_team1:
        db_session.add(
            MatchResultReply(
                match_id=match.id,
                user_id=player.user.id,
                result="win",
                pending=True
            )
        )

    for player in voters_team2:
        db_session.add(
            MatchResultReply(
                match_id=match.id,
                user_id=player.user.id,
                result="loss",
                pending=True
            )
        )

    db_session.commit()

    # ─────────────────────────────
    # Ejecutar cron
    # ─────────────────────────────
    dispatch_pending_notifications(db=db_session)

    db_session.refresh(match)

    assert match.winner_team_id == team1.id



@pytest.mark.nivel("medio")
def test_match_does_not_close_without_majority_or_timeout(
    client: TestClient,
    db_session: Session
):
    match, team1, team2 = utils.create_balanced_match(
        client, db_session, players_per_team=5
    )

    assert team1.players[0].user is not None
    assert team2.players[0].user is not None

    # 1 voto por equipo (empate)
    db_session.add(
        MatchResultReply(
            match_id=match.id,
            user_id=team1.players[0].user.id,
            result="win",
            pending=True
        )
    )

    db_session.add(
        MatchResultReply(
            match_id=match.id,
            user_id=team2.players[0].user.id,
            result="win",
            pending=True
        )
    )

    db_session.commit()

    dispatch_pending_notifications(db=db_session)

    db_session.refresh(match)
    assert match.winner_team_id is None


@pytest.mark.nivel("medio")
def test_match_closes_by_timeout(
    client: TestClient,
    db_session: Session
):
    match, team1, team2 = utils.create_balanced_match(
        client, db_session, players_per_team=5
    )

    # ─────────────────────────────
    # Match suficientemente viejo → timeout REAL (24h)
    # ─────────────────────────────
    match.date = datetime.utcnow() - timedelta(hours=25)
    db_session.commit()

    # ─────────────────────────────
    # Solo algunos votos (no unanimidad ni irreversible)
    # Team2 va ganando
    # ─────────────────────────────
    for player in team2.players[:2]:
        assert player.user is not None
        db_session.add(
            MatchResultReply(
                match_id=match.id,
                user_id=player.user.id,
                result="win",
                pending=True
            )
        )

    db_session.commit()

    # ─────────────────────────────
    # Ejecutar cron con now explícito
    # ─────────────────────────────
    dispatch_pending_notifications(
        db=db_session,
        now=datetime.utcnow()
    )

    db_session.refresh(match)

    # ─────────────────────────────
    # Validación
    # ─────────────────────────────
    assert match.winner_team_id == team2.id


@pytest.mark.nivel("medio")
def test_match_closes_by_unanimous_votes(
    client: TestClient,
    db_session: Session
):
    match, team1, team2 = utils.create_balanced_match(
        client, db_session, players_per_team=5
    )

    for player in team1.players + team2.players:
        assert player.user is not None
        db_session.add(
            MatchResultReply(
                match_id=match.id,
                user_id=player.user.id,
                result="win" if player in team1.players else "loss",
                pending=True
            )
        )

    db_session.commit()

    dispatch_pending_notifications(db=db_session)

    db_session.refresh(match)
    assert match.winner_team_id == team1.id



@pytest.mark.nivel("alto")
def test_multiple_matches_with_player_evaluations_and_auto_close(
    client: TestClient,
    db_session: Session
):
    # =====================
    # Crear usuario admin
    # =====================
    utils.create_player(client, "admin_user", stats=generate_stats_for_player(100))
    login_res = client.post(
        "/auth/login",
        json={"username": "admin_user", "password": "testpass"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # =====================
    # Crear jugadores
    # =====================
    player_ids = []
    for i in range(20):
        utils.create_player(client, f"player{i}", stats=generate_stats_for_player(i))
        player = db_session.query(Player).filter_by(name=f"player{i}").first()
        assert player is not None
        player_ids.append(player.id)

    num_matches = 10
    players_per_match = 10  # 5 vs 5

    for _ in range(num_matches):
        selected_player_ids = random.sample(player_ids, players_per_match)

        # =====================
        # Crear match
        # =====================
        match_id = utils.create_match(client, players_per_match)
        match = db_session.query(Match).get(match_id)
        assert match is not None

        utils.assign_players_randomly(
            client, db_session, match.id, selected_player_ids
        )

        # =====================
        # Generar equipos
        # =====================
        res = client.post(
            f"/match/matches/{match.id}/generate-teams",
            headers=headers
        )
        assert res.status_code == 200

        db_session.refresh(match)
        assert match.team1_id and match.team2_id

        team1 = db_session.query(Team).get(match.team1_id)
        team2 = db_session.query(Team).get(match.team2_id)

        assert len(team1.players) == players_per_match / 2
        assert len(team2.players) == players_per_match / 2

        # =====================
        # Simular notificaciones
        # =====================
        winning_team = random.choice([team1, team2])
        losing_team = team2 if winning_team.id == team1.id else team1

        for player in team1.players + team2.players:
            notif = Notification(
                user_id=player.user_id,
                event_type="MATCH_RESULT",
                channel="telegram",
                status="pending",
                available_at=datetime.utcnow() - timedelta(seconds=1),
                payload={
                    "match_id": match.id,
                    "team1_id": team1.id,
                    "team2_id": team2.id,
                }
            )
            db_session.add(notif)

        db_session.commit()

        # =====================
        # Simular replies
        # =====================
        all_players = team1.players + team2.players

        winning_players = winning_team.players
        losing_players = losing_team.players

        forced_winners = set(
            random.sample(winning_players, k=min(7, len(winning_players)))
        )

        for player in all_players:
            reply = MatchResultReply(
                match_id=match.id,
                user_id=player.user_id,
                result="win" if player in forced_winners else "loss",
                pending=True
            )
            db_session.add(reply)

        db_session.commit()

        # =====================
        # Ejecutar cron
        # =====================
        dispatch_pending_notifications(
            db=db_session,
            now=datetime.utcnow()
        )

        db_session.refresh(match)
        assert match.winner_team_id == winning_team.id

        # =====================
        # Simular evaluaciones
        # =====================
        match_players = (
            db_session.query(Player)
            .filter(Player.id.in_(selected_player_ids))
            .all()
        )

        evaluators = sorted(
            match_players, key=lambda p: p.ritmo, reverse=True
        )[:2]

        for evaluator in evaluators:
            targets = [p for p in match_players if p.id != evaluator.id]
            for target in random.sample(targets, k=min(3, len(targets))):
                new_ritmo = min(target.ritmo + 5, 100)
                stats_input = PlayerStatsUpdate(ritmo=new_ritmo)

                updated = update_player_stats(
                    target_username=target.name,
                    evaluator_username=evaluator.name,
                    stats_data=stats_input,
                    db=db_session
                )

                assert updated.ritmo >= target.ritmo

    # =====================
    # Validaciones finales
    # =====================
    players = db_session.query(Player).filter(Player.id.in_(player_ids)).all()

    multiples_partidos = [p for p in players if p.cant_partidos > 1]
    assert len(multiples_partidos) > 0

    found_relation = False
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            relation = get_or_create_relation(
                players[i].id,
                players[j].id,
                db=db_session
            )
            if relation.games_together + relation.games_apart > 0:
                found_relation = True
                break
        if found_relation:
            break

    assert found_relation, "No se encontraron relaciones entre jugadores"
