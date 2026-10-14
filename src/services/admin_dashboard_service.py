"""Read-only administration analytics and explicit, non-sensitive entity views."""
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import selectinload

from src.models import AdminMetricSnapshot, Player, Match, MatchPlayer, League, LeagueMember, AchievementDefinition, AchievementAward, User
from src.services.achievement_definition_service import serialize
from src.services.admin_service import get_admin_summary


MODELS = {"players": Player, "matches": Match, "leagues": League, "awards": AchievementDefinition}

SNAPSHOT_SERIES = {
    "players": ("Registrados", "Sin partidos", "Con 1+ partido"),
    "matches": ("Jugados", "Programados"),
    "leagues": ("Creadas", "Activas con partidos jugados"),
    "league_memberships": ("Membresías", "Con partido en la liga", "Sin participar"),
    "activity_levels": ("Inicial", "Partidos", "Completo"),
    "awards": ("Entregados", "Premios y logros definidos"),
}


def snapshot_series(db, snapshot_date, metrics, days):
    """Persist one daily aggregate and return only genuinely captured dates."""
    snapshot = db.query(AdminMetricSnapshot).filter_by(snapshot_date=snapshot_date).one_or_none()
    if snapshot is None:
        db.add(AdminMetricSnapshot(snapshot_date=snapshot_date, metrics=metrics))
        db.commit()
    elif snapshot.metrics != metrics:
        snapshot.metrics = metrics
        db.commit()

    start_date = snapshot_date - timedelta(days=days - 1)
    rows = db.query(AdminMetricSnapshot).filter(
        AdminMetricSnapshot.snapshot_date >= start_date,
        AdminMetricSnapshot.snapshot_date <= snapshot_date,
    ).order_by(AdminMetricSnapshot.snapshot_date.asc()).all()
    dates = [row.snapshot_date.isoformat() for row in rows]
    return dates, {
        key: [{"name": name, "values": [row.metrics.get(key, {}).get(name, 0) for row in rows]} for name in names]
        for key, names in SNAPSHOT_SERIES.items()
    }


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

    # A membership is only participative when the same player appears in a
    # match associated with the same league. Scheduled matches count: this is
    # an audit of membership use, not a result-closure metric.
    human_member_filter = (Player.is_bot.is_(False), or_(User.id.is_(None), User.is_admin.is_(False)))
    membership_pairs = set(db.query(LeagueMember.player_id, LeagueMember.league_id).join(
        Player, LeagueMember.player_id == Player.id
    ).outerjoin(User, Player.user_id == User.id).filter(*human_member_filter).all())
    participating_membership_pairs = set(db.query(LeagueMember.player_id, LeagueMember.league_id).join(
        Player, LeagueMember.player_id == Player.id
    ).outerjoin(User, Player.user_id == User.id).join(
        MatchPlayer, MatchPlayer.player_id == LeagueMember.player_id
    ).join(Match, Match.id == MatchPlayer.match_id).filter(
        Match.league_id == LeagueMember.league_id, *human_member_filter
    ).distinct().all()) & membership_pairs
    membership_by_player = {}
    participating_by_player = {}
    for player_id, _league_id in membership_pairs:
        membership_by_player[player_id] = membership_by_player.get(player_id, 0) + 1
    for player_id, _league_id in participating_membership_pairs:
        participating_by_player[player_id] = participating_by_player.get(player_id, 0) + 1
    member_names = dict(db.query(Player.id, Player.name).filter(Player.id.in_(membership_by_player)).all()) if membership_by_player else {}
    membership_audit = sorted((
        [member_names.get(player_id, f"Jugador #{player_id}"), memberships, participating_by_player.get(player_id, 0), memberships - participating_by_player.get(player_id, 0)]
        for player_id, memberships in membership_by_player.items()
    ), key=lambda row: (-row[3], -row[1], row[0].lower()))
    real_player_rows = real_players.with_entities(Player.id, Player.name).all()
    real_player_ids = [player_id for player_id, _name in real_player_rows]
    match_counts_by_player = dict(db.query(
        MatchPlayer.player_id, func.count(MatchPlayer.id)
    ).filter(MatchPlayer.player_id.in_(real_player_ids)).group_by(MatchPlayer.player_id).all()) if real_player_ids else {}
    owned_leagues_by_player = dict(db.query(
        League.owner_player_id, func.count(League.id)
    ).filter(League.owner_player_id.in_(real_player_ids)).group_by(League.owner_player_id).all()) if real_player_ids else {}
    activity_levels = {"Inicial": 0, "Partidos": 0, "Completo": 0}
    activity_audit = []
    for player_id, name in real_player_rows:
        matches = match_counts_by_player.get(player_id, 0)
        memberships = membership_by_player.get(player_id, 0)
        owned_leagues = owned_leagues_by_player.get(player_id, 0)
        level = "Inicial" if not matches else "Completo" if memberships or owned_leagues else "Partidos"
        activity_levels[level] += 1
        activity_audit.append([name, level, matches, memberships, owned_leagues])
    activity_audit.sort(key=lambda row: ({"Inicial": 0, "Partidos": 1, "Completo": 2}[row[1]], -row[2], -row[3], row[0].lower()))
    activity_total = len(real_player_rows)
    activity_percentages = {
        level: round(count * 100 / activity_total, 1) if activity_total else 0
        for level, count in activity_levels.items()
    }

    activity_end = now + timedelta(days=days)
    league_activity = db.query(
        League.id.label("id"), League.name.label("name"), func.count(Match.id).label("matches")
    ).outerjoin(
        Match, (Match.league_id == League.id) & (Match.date >= start) & (Match.date <= activity_end)
    ).group_by(League.id, League.name)
    active_league_ids = db.query(League.id).filter(
        League.start_date <= now.date(), League.end_date >= now.date(),
        League.id.in_(db.query(Match.league_id).filter(
            Match.league_id.isnot(None), Match.date <= now, completed_condition
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
                  active_leagues=active_league_ids.count(), league_memberships=len(membership_pairs),
                  participating_league_memberships=len(participating_membership_pairs),
                  unused_league_memberships=len(membership_pairs - participating_membership_pairs),
                  players_with_unused_league_memberships=sum(
                      memberships > participating_by_player.get(player_id, 0)
                      for player_id, memberships in membership_by_player.items()
                   ))
    snapshot_metrics = {
        "players": {"Registrados": totals["real_players"], "Sin partidos": totals["players_without_matches"], "Con 1+ partido": totals["players_with_matches"]},
        "matches": {"Jugados": totals["completed_matches"], "Programados": totals["upcoming_matches"]},
        "leagues": {"Creadas": totals["leagues"], "Activas con partidos jugados": totals["active_leagues"]},
        "league_memberships": {"Membresías": totals["league_memberships"], "Con partido en la liga": totals["participating_league_memberships"], "Sin participar": totals["unused_league_memberships"]},
        "activity_levels": {"Inicial": activity_percentages["Inicial"], "Partidos": activity_percentages["Partidos"], "Completo": activity_percentages["Completo"]},
        "awards": {"Entregados": totals["awarded"], "Premios y logros definidos": totals["awards"]},
    }
    snapshot_dates, series_by_key = snapshot_series(db, now.date(), snapshot_metrics, days)
    capture_note = "Las series comienzan con la primera medición disponible; no se reconstruyen datos históricos."
    return {
        "totals": totals,
        "days": days,
        "generated_at": now.isoformat() + "Z",
        "dates": snapshot_dates,
        "charts": [
            {"key": "players", "title": "Jugadores",
             "note": "Solo perfiles humanos registrados. Un partido programado ya cuenta como participación.",
              "series": series_by_key["players"], "snapshot_note": capture_note},
            {"key": "matches", "title": "Partidos",
             "note": "Finalizados hasta ahora y programados para una fecha futura.",
              "series": series_by_key["matches"], "snapshot_note": capture_note},
            {"key": "leagues", "title": "Ligas",
             "note": f"Frecuencia de uso: partidos asociados entre {start.date().isoformat()} y {activity_end.date().isoformat()}.",
              "series": series_by_key["leagues"], "snapshot_note": capture_note,
             "breakdown": {"headers": ["Liga", "Partidos en el período"],
                           "rows": [[row.name, row.matches] for row in league_activity.order_by(func.count(Match.id).desc(), League.name.asc()).all()]}},
            {"key": "league_memberships", "view": "players", "title": "Adhesión de jugadores a ligas",
             "note": f"Cada jugador se compara contra las {totals['leagues']} ligas creadas. Revisá las membresías sin partido asociado.",
              "series": series_by_key["league_memberships"], "snapshot_note": capture_note,
             "breakdown": {"title": f"Jugadores a revisar: {totals['players_with_unused_league_memberships']}",
                           "headers": ["Jugador", "Ligas unidas / total", "Con partido", "Sin participar"],
                           "rows": [[name, f"{memberships} / {totals['leagues']}", participating, unused]
                                    for name, memberships, participating, unused in membership_audit]}},
            {"key": "activity_levels", "view": "players", "title": "Nivel de actividad de jugadores",
             "unit": "%",
             "note": f"Distribución sobre {activity_total} jugadores reales. Inicial: sin partidos; Partidos: usa partidos, sin ligas; Completo: usa partidos y ligas.",
              "series": series_by_key["activity_levels"], "snapshot_note": capture_note,
             "breakdown": {"title": f"Jugadores reales clasificados: {len(activity_audit)}",
                           "headers": ["Jugador", "Nivel", "Partidos", "Ligas unidas", "Ligas creadas"],
                           "rows": activity_audit}},
            {"key": "awards", "title": "Premios y logros",
             "note": "Entregas acumuladas y premios ordenados por cantidad de jugadores que los recibieron.",
              "series": series_by_key["awards"], "snapshot_note": capture_note,
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
