"""Read-only global activity feed for the Mini App news ticker."""

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from src.models import AchievementAward, AchievementDefinition, Match, Player
from src.models.team import Team


def _names(players: list[Player]) -> str:
    names = [player.name for player in players if not player.is_bot]
    if not names:
        return "El equipo"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} y {names[1]}"
    return f"{names[0]}, {names[1]} y {len(names) - 2} más"


def global_news(db: Session, limit: int = 12) -> list[dict]:
    """Return recent platform-wide match, award, and upcoming-match news."""
    now = datetime.utcnow()
    fetch_limit = max(limit, 1)
    items: list[dict] = []

    awards = db.query(AchievementAward, AchievementDefinition, Player).join(
        AchievementDefinition, AchievementDefinition.id == AchievementAward.achievement_id
    ).join(
        Player, Player.id == AchievementAward.player_id
    ).filter(
        Player.is_bot.is_(False),
    ).order_by(AchievementAward.earned_at.desc()).limit(fetch_limit).all()
    for award, definition, player in awards:
        items.append({
            "kind": "award",
            "message": f"{player.name} obtuvo {definition.name}",
            "occurred_at": award.earned_at,
        })

    completed = db.query(Match).options(
        selectinload(Match.team1).selectinload(Team.players),
        selectinload(Match.team2).selectinload(Team.players),
    ).filter(
        or_(Match.winner_team_id.isnot(None), Match.is_draw.is_(True)),
    ).order_by(Match.date.desc()).limit(fetch_limit).all()
    for match in completed:
        if match.is_draw:
            players = (match.team1.players if match.team1 else []) + (match.team2.players if match.team2 else [])
            message = f"Partido #{match.id}: {_names(players)} empataron"
        else:
            winners = match.team1 if match.winner_team_id == match.team1_id else match.team2
            message = f"{_names(winners.players if winners else [])} ganaron el partido #{match.id}"
        items.append({"kind": "result", "message": message, "occurred_at": match.date})

    upcoming = db.query(Match).filter(
        Match.date > now,
        Match.winner_team_id.is_(None),
        Match.is_draw.is_(False),
    ).order_by(Match.date.asc()).limit(fetch_limit).all()
    for match in upcoming:
        items.append({
            "kind": "upcoming",
            "message": f"Próximo partido #{match.id}",
            "occurred_at": match.date,
        })

    items.sort(key=lambda item: item["occurred_at"], reverse=True)
    return [
        {**item, "occurred_at": item["occurred_at"].isoformat() + "Z"}
        for item in items[:limit]
    ]
