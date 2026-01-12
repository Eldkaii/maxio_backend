import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import random
from src.main import app
from src.models import Player, Team, Match
from src.services.match_service import assign_match_winner
from src.services.player_service import build_full_player_profile
from src.test.utils_common_methods import TestUtils
from src.utils.logger_config import test_logger as logger

utils = TestUtils()
client = TestClient(app)


@pytest.mark.nivel("medio")
def test_build_player_profile_basic(client: TestClient, db_session: Session):
    # Crear player
    utils.create_player(client, "simple_player")

    profile = build_full_player_profile(
        db=db_session,
        username="simple_player",
        recent_matches_limit=5
    )

    logger.info("PERFIL BÁSICO DEL PLAYER:\n%s", profile)

    # ---- Validaciones base ----
    assert profile["name"] == "simple_player"
    assert profile["is_bot"] is False

    # ---- Stats ----
    stats = profile["stats"]
    for key in ["tiro", "ritmo", "fisico", "defensa", "aura", "elo"]:
        assert key in stats

    # ---- Summary ----
    summary = profile["matches_summary"]
    assert summary["played"] == 0
    assert summary["won"] == 0
    assert summary["winrate"] == 0.0
    assert summary["recent_results"] == []

    # ---- Relaciones ----
    relations = profile["relations"]
    assert relations["top_allies"] == []
    assert relations["top_opponents"] == []
    assert relations["most_played_with"] == []

    # ---- Matches ----
    assert profile["recent_matches"] == []

    # ---- Evaluations ----
    evaluation = profile["evaluation"]
    assert evaluation["can_evaluate"] == []

@pytest.mark.nivel("alto")
def test_build_player_profile_full(client: TestClient, db_session: Session):
    # Crear admin y autenticarse
    utils.create_player(client, "admin_user")
    login = client.post("/auth/login", json={"username": "admin_user", "password": "testpass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Crear jugadores
    player_names = ["Tp1", "Tp2", "Tp3", "Tp4", "Tp5", "Tp6"]
    for name in player_names:
        utils.create_player(client, name)

    players = db_session.query(Player).filter(Player.name.in_(player_names)).all()
    assert len(players) == len(player_names)

    target_player = players[0]

    # Crear match
    match_id = utils.create_match(client, max_players=6)
    match = db_session.query(Match).get(match_id)
    assert match is not None

    utils.assign_players_randomly(
        client=client,
        db_session=db_session,
        match_id=match.id,
        player_ids=[p.id for p in players]
    )

    # Generar equipos
    res = client.post(f"/match/matches/{match.id}/generate-teams", headers=headers)
    assert res.status_code == 200

    db_session.refresh(match)

    team1 = db_session.query(Team).get(match.team1_id)
    team2 = db_session.query(Team).get(match.team2_id)

    winning_team = random.choice([team1, team2])
    assign_match_winner(match=match, winning_team=winning_team, db=db_session)

    # ---- Construir perfil ----
    profile = build_full_player_profile(
        db=db_session,
        username=target_player.name,
        recent_matches_limit=5
    )

    logger.info("PERFIL COMPLETO DEL PLAYER:\n%s", profile)

    # ---- Validaciones base ----
    assert profile["id"] == target_player.id
    assert profile["name"] == target_player.name

    # ---- Stats ----
    assert profile["stats"]["elo"] > 0

    # ---- Matches summary ----
    summary = profile["matches_summary"]
    assert summary["played"] >= 1

    # ---- Recent matches ----
    recent_matches = profile["recent_matches"]
    assert len(recent_matches) == 1

    match_info = recent_matches[0]
    assert match_info["match_id"] == match.id
    assert match_info["team"] in ["team1", "team2"]
    assert match_info["result"] in ["win", "loss"]

    assert len(match_info["teammates"]) > 0
    assert len(match_info["opponents"]) > 0

    # ---- Relaciones ----
    relations = profile["relations"]
    assert isinstance(relations["most_played_with"], list)

    # ---- Evaluations ----
    evaluation = profile["evaluation"]
    assert "can_evaluate" in evaluation
    assert isinstance(evaluation["can_evaluate"], list)