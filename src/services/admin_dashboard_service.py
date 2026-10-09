"""Read-only administration analytics and explicit, non-sensitive entity views."""
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import Date, String, cast, func, or_
from sqlalchemy.orm import selectinload

from src.models import Player, Match, MatchPlayer, League, LeagueMember, AchievementDefinition, AchievementAward
from src.services.achievement_definition_service import serialize
from src.services.admin_service import get_admin_summary


MODELS = {"players": Player, "matches": Match, "leagues": League, "awards": AchievementDefinition}


def dashboard_metrics(db, days=30):
    now = datetime.utcnow()
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    dates = [(start + timedelta(days=i)).date() for i in range(days)]

    def series(query, date_column, count_column, distinct=False):
        day = cast(date_column, Date)
        count = func.count(func.distinct(count_column)) if distinct else func.count(count_column)
        rows = query.with_entities(day, count).filter(date_column >= start, date_column <= now).group_by(day).all()
        values = dict(rows)
        return [values.get(d, 0) for d in dates]

    played = db.query(Match).filter(or_(Match.winner_team_id.isnot(None), Match.is_draw.is_(True)))
    participations = db.query(MatchPlayer).join(Match).join(Player).filter(Player.is_bot.is_(False))
    first = participations.with_entities(Player.id.label("id"), func.min(Match.date).label("date")).filter(
        Match.date <= now, or_(Match.winner_team_id.isnot(None), Match.is_draw.is_(True))
    ).group_by(Player.id).subquery()
    active = participations.filter(or_(Match.winner_team_id.isnot(None), Match.is_draw.is_(True)))
    totals = get_admin_summary(db)
    totals.update(awards=db.query(AchievementDefinition).count(), awarded=db.query(AchievementAward).count(),
                  completed_matches=played.count(), active_players=active.filter(Match.date >= start, Match.date <= now).with_entities(Player.id).distinct().count())
    return {"totals": totals, "dates": [d.isoformat() for d in dates], "days": days,
            "generated_at": now.isoformat() + "Z", "charts": [
        {"key": "players", "title": "Jugadores", "note": "Humanos: primer partido finalizado y jugadores únicos por día. No representa altas de cuentas.",
         "series": [{"name": "Debutantes", "values": series(db.query(first), first.c.date, first.c.id)},
                    {"name": "Activos", "values": series(active, Match.date, Player.id, True)}]},
        {"key": "matches", "title": "Partidos", "note": "Por fecha del encuentro (UTC), no por fecha de creación. Excluye fechas futuras.",
         "series": [{"name": "Programados", "values": series(db.query(Match), Match.date, Match.id)},
                    {"name": "Finalizados", "values": series(played, Match.date, Match.id)}]},
        {"key": "leagues", "title": "Ligas", "note": "Inicio de temporadas y ligas con encuentros finalizados por día; no son altas de ligas.",
         "series": [{"name": "Temporadas iniciadas", "values": series(db.query(League), League.start_date, League.id)},
                    {"name": "Con actividad", "values": series(played.filter(Match.league_id.isnot(None)), Match.date, Match.league_id, True)}]},
        {"key": "awards", "title": "Premios", "note": "Definiciones creadas y entregas registradas de logros y trofeos (UTC).",
         "series": [{"name": "Nuevos premios", "values": series(db.query(AchievementDefinition), AchievementDefinition.created_at, AchievementDefinition.id)},
                    {"name": "Entregas", "values": series(db.query(AchievementAward), AchievementAward.earned_at, AchievementAward.id)}]},
    ]}


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
