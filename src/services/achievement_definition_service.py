from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from src.models import AchievementAward, AchievementDefinition

TROPHY_DIR = Path(__file__).resolve().parents[1] / "images" / "trofeos"
DEFAULTS = (
    ("matches-1", "Debutante", "Primer partido jugado", {"played": 1}),
    ("matches-5", "Habitual", "Cinco partidos jugados", {"played": 5}),
    ("matches-10", "De la casa", "Diez partidos jugados", {"played": 10}),
    ("matches-25", "Referente", "Veinticinco partidos jugados", {"played": 25}),
    ("wins-1", "Primera alegría", "Primera victoria", {"wins": 1}),
    ("wins-5", "Cinco festejos", "Cinco victorias", {"wins": 5}),
    ("winrate-60", "Eficacia", "60% de victorias", {"winrate": 60}),
    ("with-games-5", "Socios de cancha", "Cinco partidos con el mismo jugador", {"with_games": 5}),
    ("skill-aura-80", "Presencia", "Aura de 80 o más", {"skill_aura": 80}),
)


def seed_default_achievements(db: Session):
    for key, name, description, conditions in DEFAULTS:
        if not db.query(AchievementDefinition).filter_by(key=key).first():
            db.add(AchievementDefinition(key=key, name=name, description=description, conditions=conditions))
    db.flush()


def trophy_images():
    if not TROPHY_DIR.exists():
        return []
    source_sheets = {
        "Colección de Insignias Futbolísticas de Élite.png",
        "Colección de trofeos deportivos 3D.png",
        "Colección de Trofeos Deportivos en 3D.png",
    }
    return sorted(
        f.name
        for f in TROPHY_DIR.iterdir()
        if f.suffix.lower() == ".png"
        and f.name not in source_sheets
        and not f.name.startswith("Diseño sin título (")
    )


def reward_kind(definition):
    if definition.reward_type in ("achievement", "trophy"):
        return definition.reward_type
    # Compatibility for existing definitions: photographed cups are trophies;
    # the first three assets are medals. Administrators can override this.
    cups = {f"trofeo-real-{i:02d}.png" for i in range(4, 24)}
    conditions = definition.conditions or {}
    if (definition.trophy_image in cups or float(conditions.get("wins", 0)) >= 100
            or any(float(value) >= 90 for key, value in conditions.items() if key.startswith("skill_"))):
        return "trophy"
    return "achievement"


def serialize(definition):
    return {"id": definition.id, "key": definition.key, "name": definition.name,
            "description": definition.description, "conditions": definition.conditions or {},
            "trophy_image": definition.trophy_image, "active": definition.active,
            "reward_type": reward_kind(definition)}


def list_definitions(db):
    seed_default_achievements(db)
    return [serialize(item) for item in db.query(AchievementDefinition).order_by(AchievementDefinition.id).all()]


def _peer_progress(player):
    relations = getattr(player, "all_relationships", [])
    together = max((int(r.games_together or 0) for r in relations), default=0)
    wins_by_peer = {}
    for match in getattr(player, "matches", []):
        current = next((item for item in match.match_associations if item.player_id == player.id), None)
        if not current or not match.winner_team_id:
            continue
        winning_team = str(getattr(current.team, "value", current.team))
        team_id = match.team1_id if winning_team == "team1" else match.team2_id
        if team_id != match.winner_team_id:
            continue
        for item in match.match_associations:
            if item.player_id != player.id and str(getattr(item.team, "value", item.team)) == winning_team:
                wins_by_peer[item.player_id] = wins_by_peer.get(item.player_id, 0) + 1
    return together, max(wins_by_peer.values(), default=0)


def evaluate_player_achievements(db: Session, player):
    if player.is_bot:
        return []
    seed_default_achievements(db)
    played = int(player.cant_partidos or 0)
    wins = int(player.cant_partidos_ganados or 0)
    winrate = (wins * 100 / played) if played else 0
    with_games, with_wins = _peer_progress(player)
    values = {"played": played, "wins": wins, "winrate": winrate,
              "with_games": with_games, "with_wins": with_wins,
              "skill_tiro": player.tiro, "skill_ritmo": player.ritmo,
              "skill_fisico": player.fisico, "skill_defensa": player.defensa,
              "skill_aura": player.aura}
    result = []
    for definition in db.query(AchievementDefinition).filter_by(active=True).all():
        conditions = definition.conditions or {}
        progress = 0
        earned = True
        for key, target in conditions.items():
            current = float(values.get(key, 0) or 0)
            progress = max(progress, int(current))
            if current < float(target):
                earned = False
        award = db.query(AchievementAward).filter_by(achievement_id=definition.id, player_id=player.id).first()
        if earned and not award:
            award = AchievementAward(achievement_id=definition.id, player_id=player.id, progress=progress,
                                     earned_at=datetime.utcnow())
            db.add(award)
        if award:
            earned = True
            progress = max(progress, int(award.progress or 0))
        result.append({"key": definition.key, "name": definition.name, "metric": "personalizado",
                       "progress": progress, "target": max([int(v) for v in conditions.values()] or [1]),
                       "earned": earned, "reward": definition.description, "peer": None,
                       "trophy_image": definition.trophy_image,
                       "earned_at": award.earned_at.isoformat() + "Z" if award and award.earned_at else None,
                       "conditions": conditions,
                       "reward_type": reward_kind(definition),
                       "family": "+".join(sorted(conditions)) or definition.key})
    if db.dirty or db.new:
        db.commit()
    return result
