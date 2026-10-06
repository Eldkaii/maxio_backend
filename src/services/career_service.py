"""Read-only career progression from settled statistics; no database or config imports."""

STAGES = (
    (0, "Recién llegado", "Por empezar", "Tu historia empieza con un partido."),
    (1, "Debutante", "Debut registrado", "El primer partido deja su marca."),
    (5, "Habitual", "Cinco partidos registrados", "La constancia empieza a notarse."),
    (10, "De la casa", "Diez partidos registrados", "Tu historia ya forma parte del barrio."),
    (25, "Referente", "Veinticinco partidos registrados", "Una historia que sigue creciendo."),
    (50, "Histórico", "Cincuenta partidos registrados", "Cincuenta encuentros compartidos."),
    (100, "Leyenda del barrio", "Cien partidos registrados", "Cien partidos. Una historia que queda."),
)


def build_career(played, won, peers=(), *, is_bot=False):
    """Peers are all human relations, not the truncated profile leaderboards.

    Titles measure participation, independently of ELO. No dates or historical
    win streaks are inferred from the limited recent-results buffer.
    """
    played, won = max(0, int(played or 0)), max(0, int(won or 0))
    if is_bot:
        return None
    milestones = []
    stage_index = max(i for i, stage in enumerate(STAGES) if played >= stage[0])
    for target, title, reward, _ in STAGES[1:]:
        milestones.append(dict(key=f"matches-{target}", name=title, metric="partidos",
                               progress=min(played, target), target=target,
                               earned=played >= target, reward=reward, peer=None))
    for target, title in ((1, "Primera alegría"), (5, "Cinco festejos"), (20, "Veinte victorias"), (50, "Medio centenar")):
        milestones.append(dict(key=f"wins-{target}", name=title, metric="victorias",
                               progress=min(won, target), target=target,
                               earned=won >= target, reward="Victoria en tu historial", peer=None))
    connections = []
    for kind, field, names in (
        ("duo", "games_together", ((5, "Socios de cancha"), (10, "Dupla de la casa"), (25, "Sociedad histórica"))),
        ("rival", "games_apart", ((5, "La revancha"), (10, "Clásico del barrio"), (25, "Rivalidad histórica"))),
    ):
        candidates = sorted((p for p in peers if not p.get("is_bot") and int(p.get(field) or 0) > 0),
                            key=lambda p: (-int(p[field]), str(p["name"])))
        best = candidates[0] if candidates else None
        count = int(best[field]) if best else 0
        earned_names = [name for target, name in names if count >= target]
        next_target, next_name = next(((t, n) for t, n in names if count < t), names[-1])
        connections.append(dict(kind=kind, peer=best["name"] if best else None, count=count,
                                title=earned_names[-1] if earned_names else "Por construir",
                                next_name=next_name, target=next_target, complete=count >= names[-1][0]))
        # A permanent set of achievements per pair: a new leading partner does
        # not erase the badges earned with earlier partners.
        for peer in candidates:
            for target, name in names:
                if int(peer[field]) >= target:
                    milestones.append(dict(key=f"{kind}-{peer['id']}-{target}", name=name,
                                           metric="juntos" if kind == "duo" else "enfrentados",
                                           progress=target, target=target, earned=True,
                                           reward="Historia compartida", peer=peer["name"]))
    stage = STAGES[stage_index]
    return dict(title=stage[1], stage=stage_index, neighborhood=stage[2], description=stage[3],
                played=played, milestones=milestones, connections=connections,
                next_milestone=next((m for m in milestones if m["key"].startswith("matches-") and not m["earned"]), None),
                earned_count=sum(m["earned"] for m in milestones))
