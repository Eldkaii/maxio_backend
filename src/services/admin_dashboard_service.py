"""Read-only administration analytics and explicit, non-sensitive entity views."""
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import selectinload

from src.models import Player, Match, MatchPlayer, League, LeagueMember, AchievementDefinition, AchievementAward, User
from src.services.achievement_definition_service import serialize
from src.services.admin_service import get_admin_summary


MODELS = {"players": Player, "matches": Match, "leagues": League, "awards": AchievementDefinition}


def dashboard_metrics(db, days=30):
    now = datetime.utcnow()
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    completed_condition = or_(Match.winner_team_id.isnot(None), Match.is_draw.is_(True))
    played = db.query(Match).filter(Match.date <= now, completed_condition)
    upcoming = db.query(Match).filter(Match.date > now, Match.winner_team_id.is_(None), Match.is_draw.is_(False))
    real_players = db.query(Player).outerjoin(User, Player.user_id == User.id).filter(
        Player.is_bot.is_(False), or_(User.id.is_(None), User.is_admin.is_(False))
    )
    player_ids_with_matches = db.query(MatchPlayer.player_id).join(Match).distinct()
    players_with_matches = real_players.filter(Player.id.in_(player_ids_with_matches))
    players_without_matches = real_players.filter(~Player.id.in_(player_ids_with_matches))

    activity_end = now + timedelta(days=days)
    league_activity = db.query(
        League.id.label("id"), League.name.label("name"), func.count(Match.id).label("matches")
    ).outerjoin(
        Match, (Match.league_id == League.id) & (Match.date >= start) & (Match.date <= activity_end)
    ).group_by(League.id, League.name)
    active_league_ids = db.query(League.id).filter(
        League.start_date <= now.date(), League.end_date >= now.date(),
        League.id.in_(db.query(Match.league_id).filter(
            Match.league_id.isnot(None), or_(completed_condition, Match.date > now)
        )),
    )
    top_awards = db.query(
        AchievementDefinition.name.label("name"), func.count(AchievementAward.id).label("awards")
    ).outerjoin(AchievementAward).group_by(
        AchievementDefinition.id, AchievementDefinition.name
    ).order_by(func.count(AchievementAward.id).desc(), AchievementDefinition.name.asc()).limit(10).all()
    totals = get_admin_summary(db)
    totals.update(awards=db.query(AchievementDefinition).count(), awarded=db.query(AchievementAward).count(),
                  completed_matches=played.count(), upcoming_matches=upcoming.count(),
                  players_without_matches=players_without_matches.count(), players_with_matches=players_with_matches.count(),
                  active_leagues=active_league_ids.count())
    return {
        "totals": totals,
        "days": days,
        "generated_at": now.isoformat() + "Z",
        "charts": [
            {"key": "players", "title": "Jugadores",
             "note": "Solo perfiles humanos registrados. Un partido programado ya cuenta como participación.",
             "summary": [{"name": "Registrados", "value": totals["real_players"]},
                         {"name": "Sin partidos", "value": totals["players_without_matches"]},
                         {"name": "Con 1+ partido", "value": totals["players_with_matches"]}]},
            {"key": "matches", "title": "Partidos",
             "note": "Finalizados hasta ahora y programados para una fecha futura.",
             "summary": [{"name": "Jugados", "value": totals["completed_matches"]},
                         {"name": "Programados", "value": totals["upcoming_matches"]}]},
            {"key": "leagues", "title": "Ligas",
             "note": f"Frecuencia de uso: partidos asociados entre {start.date().isoformat()} y {activity_end.date().isoformat()}.",
             "summary": [{"name": "Creadas", "value": totals["leagues"]},
                         {"name": "Activas con partidos", "value": totals["active_leagues"]}],
             "breakdown": {"headers": ["Liga", "Partidos en el período"],
                           "rows": [[row.name, row.matches] for row in league_activity.order_by(func.count(Match.id).desc(), League.name.asc()).all()]}},
            {"key": "awards", "title": "Premios y logros",
             "note": "Entregas acumuladas y premios ordenados por cantidad de jugadores que los recibieron.",
             "summary": [{"name": "Entregados", "value": totals["awarded"]},
                         {"name": "Premios definidos", "value": totals["awards"]}],
             "breakdown": {"headers": ["Premio o logro", "Entregas"],
                           "rows": [[row.name, row.awards] for row in top_awards]}},
        ],
    }
def entity_row(item):
    if isinstance(item, Player):
        return {"id": item.id, "name": item.name, "type": "Bot" if item.is_bot else "Humano", "elo": item.elo,
                "played": item.cant_partidos, "wins": item.cant_partidos_ganados, "draws": item.cant_partidos_empatados,
                "stats": {key: getattr(item, key) for key in ("tiro", "ritmo", "fisico", "defensa", "aura")}}
    if isinstance(item, Match):
        closed = item.is_draw or item.winner_team_id is not None
        return {"id": item.id, "name": f"Partido #{item.id}", "date": item.date.isoformat() + "Z",
                "status": "Empate" if item.is_draw else "Finalizado" if closed else "Programado" if item.date > datetime.utcnow() else "Pendiente",
                "capacity": item.max_players, "league_id": item.league_id,
                "winner": "Equipo 1" if item.winner_team_id and item.winner_team_id == item.team1_id else "Equipo 2" if item.winner_team_id else None}
    if isinstance(item, League):
        today = datetime.utcnow().date()
        return {"id": item.id, "name": item.name, "type": "Pública" if item.is_public else "Privada",
                "start": item.start_date, "end": item.end_date,
                "status": "Próxima" if today < item.start_date else "Finalizada" if today > item.end_date else "Activa"}
    return serialize(item)


def list_entities(db, kind, search="", page=1, size=20):
    model = MODELS[kind]
    query = db.query(model)
    if search:
        term = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses = [cast(model.id, String).ilike(f"%{term}%", escape="\\")]
        if kind != "matches":
            # Treat wildcard characters as literal search text.
            clauses = [model.name.ilike(f"%{term}%", escape="\\")]
            if search.isdigit():
                clauses.append(cast(model.id, String) == search)
        query = query.filter(or_(*clauses))
    return {"items": [entity_row(item) for item in query.order_by(model.id.desc()).offset((page - 1) * size).limit(size)],
            "total": query.count(), "page": page, "size": size}


def entity_detail(db, kind, entity_id):
    item = db.get(MODELS[kind], entity_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    result = entity_row(item)
    if kind == "matches":
        rows = db.query(MatchPlayer).options(selectinload(MatchPlayer.player)).filter_by(match_id=item.id).all()
        result["players"] = [{"id": r.player_id, "name": r.player.name, "team": r.team.value if r.team else "Sin equipo"} for r in rows]
        result["votes"] = {"Equipo 1": item.vote_win_team1, "Equipo 2": item.vote_win_team2, "Empate": item.vote_draw}
    elif kind == "leagues":
        rows = db.query(LeagueMember).options(selectinload(LeagueMember.player), selectinload(LeagueMember.rankings)).filter_by(league_id=item.id).all()
        result["members"] = [{"id": r.player_id, "name": r.player.name, "role": r.role,
                              "rankings": [{"type": k.ranking_type, "points": k.points, "played": k.matches_played, "wins": k.wins} for k in r.rankings]} for r in rows]
        result["matches"] = [entity_row(m) for m in db.query(Match).filter_by(league_id=item.id).order_by(Match.date.desc()).limit(100)]
        result["match_count"] = db.query(Match).filter_by(league_id=item.id).count()
    elif kind == "players":
        result["matches"] = [entity_row(m) for m in db.query(Match).join(MatchPlayer).filter(MatchPlayer.player_id == item.id).order_by(Match.date.desc()).limit(100)]
        result["leagues"] = [entity_row(l) for l in db.query(League).join(LeagueMember).filter(LeagueMember.player_id == item.id)]
        result["awards"] = [{"name": a.name, "earned_at": award.earned_at} for award, a in db.query(AchievementAward, AchievementDefinition).join(AchievementDefinition).filter(AchievementAward.player_id == item.id)]
    else:
        result["award_count"] = db.query(AchievementAward).filter_by(achievement_id=item.id).count()
        result["recipients"] = [{"id": p.id, "name": p.name, "earned_at": a.earned_at} for a, p in db.query(AchievementAward, Player).join(Player, Player.id == AchievementAward.player_id).filter(AchievementAward.achievement_id == item.id).order_by(AchievementAward.earned_at.desc()).limit(100)]
    return result
