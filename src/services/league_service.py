from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from src.models import League, LeagueMember, LeagueRanking, Player, User


COUNTRY_LEAGUE_NAMES = {"UY": "UY 🇺🇾"}
RANKING_TYPES = ("general", "solo_duo", "grupo")


def division_for_points(points: int) -> str:
    """Devuelve la división correspondiente; los límites superiores son exclusivos."""
    if points < 15:
        return "Bronce"
    if points < 40:
        return "Plata"
    if points < 80:
        return "Oro"
    return "Diamante"


def _ensure_league_member(db: Session, league_id: int, player_id: int, role: str = "member") -> None:
    """Add a membership only when it does not already exist.

    Do not rely on ``league.members`` here: the relationship collection can be
    stale while another membership is still pending in the same transaction.
    The query triggers SQLAlchemy's autoflush before checking the unique pair.
    """
    exists = db.query(LeagueMember.id).filter(
        LeagueMember.league_id == league_id,
        LeagueMember.player_id == player_id,
    ).first()
    if not exists:
        db.add(LeagueMember(league_id=league_id, player_id=player_id, role=role))


def ensure_member_rankings(db: Session, membership: LeagueMember) -> list[LeagueRanking]:
    """Ensures the three rankings owned by a league member exist."""
    db.flush()
    existing = {ranking.ranking_type: ranking for ranking in membership.rankings}
    for ranking_type in RANKING_TYPES:
        if ranking_type not in existing:
            ranking = LeagueRanking(league_member_id=membership.id, ranking_type=ranking_type)
            db.add(ranking)
            existing[ranking_type] = ranking
    db.flush()
    return [existing[ranking_type] for ranking_type in RANKING_TYPES]


def get_league_or_404(db: Session, league_id: int) -> League:
    league = db.query(League).options(
        joinedload(League.owner),
        joinedload(League.members).joinedload(LeagueMember.player),
    ).filter(League.id == league_id).first()
    if not league:
        raise HTTPException(status_code=404, detail="Liga no encontrada")
    return league


def _require_current_player(user: User) -> Player:
    if not user.player:
        raise HTTPException(status_code=403, detail="El usuario no tiene un jugador asociado")
    return user.player


def can_manage_league(league: League, user: User) -> bool:
    if user.is_admin:
        return True
    player = user.player
    if not player:
        return False
    return league.owner_player_id == player.id or any(
        member.player_id == player.id and member.role == "admin"
        for member in league.members
    )


def require_league_admin(league: League, user: User) -> None:
    if not can_manage_league(league, user):
        raise HTTPException(status_code=403, detail="Solo los administradores de la liga pueden realizar esta acción")


def create_league(
    db: Session,
    user: User,
    name: str,
    is_public: bool = False,
    is_special: bool = False,
    max_group_size: int | None = None,
    member_usernames: list[str] | None = None,
) -> League:
    owner = None if user.is_admin else _require_current_player(user)
    if owner:
        created_count = db.query(League).filter(League.owner_player_id == owner.id).count()
        if created_count >= 3:
            raise HTTPException(status_code=403, detail="Cada jugador puede crear hasta 3 ligas")
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="El nombre de la liga no puede estar vacío")
    existing = db.query(League).filter(League.name.ilike(normalized_name)).all()
    if is_special and not user.is_admin:
        raise HTTPException(status_code=403, detail="Solo un administrador global puede crear ligas especiales")
    # Las repeticiones de nombre se reservan exclusivamente a ligas especiales
    # creadas por administración (por ejemplo, país o departamento).
    if existing and (not is_special or any(not league.is_special for league in existing)):
        raise HTTPException(status_code=409, detail="Ya existe una liga con ese nombre")

    selected_players: list[Player] = []
    selected_ids: set[int] = set()
    for raw_username in member_usernames or []:
        username = raw_username.strip()
        if not username:
            raise HTTPException(status_code=400, detail="El nombre de un jugador no puede estar vacío")
        player = db.query(Player).filter(Player.name.ilike(username)).first()
        if not player or player.is_bot:
            raise HTTPException(status_code=404, detail=f"Jugador real no encontrado: {username}")
        if player.id not in selected_ids:
            selected_ids.add(player.id)
            selected_players.append(player)

    league = League(
        name=normalized_name,
        is_public=is_public,
        is_special=is_special,
        has_divisions=user.is_admin,
        max_group_size=max_group_size,
        owner_player_id=owner.id if owner else None,
    )
    db.add(league)
    db.flush()
    members_to_create: list[tuple[Player, str]] = []
    if owner:
        members_to_create.append((owner, "admin"))
    members_to_create.extend(
        (player, "member") for player in selected_players
        if not owner or player.id != owner.id
    )
    for player, role in members_to_create:
        membership = LeagueMember(league_id=league.id, player_id=player.id, role=role)
        db.add(membership)
        db.flush()
        ensure_member_rankings(db, membership)
    db.commit()
    return get_league_or_404(db, league.id)


def ensure_country_leagues(db: Session, country_code: str) -> list[League]:
    """Creates and synchronizes the single public national league per country."""
    country = country_code.strip().upper()
    league_name = COUNTRY_LEAGUE_NAMES.get(country)
    if not league_name:
        return []
    leagues = db.query(League).filter(
        League.country_code == country,
        League.is_system_managed.is_(True),
    ).order_by(League.id).all()
    if leagues:
        league = leagues[0]
    else:
        league = League(
            name=league_name,
            is_public=True,
            is_special=True,
            is_system_managed=True,
            has_divisions=True,
            country_code=country,
        )
        db.add(league)
        db.flush()
    league.name = league_name
    league.is_public = True
    league.is_special = True
    league.is_system_managed = True
    league.has_divisions = True
    players = db.query(Player).join(User, Player.user_id == User.id).filter(
        Player.is_bot.is_(False),
        User.nationality == country,
    ).all()
    for player in players:
        _ensure_league_member(db, league.id, player.id)
    db.flush()
    memberships = db.query(LeagueMember).filter(LeagueMember.league_id == league.id).all()
    for membership in memberships:
        ensure_member_rankings(db, membership)
    return [league]


def sync_player_country_league(db: Session, player: Player, country_code: str) -> None:
    """Mantiene la inscripción obligatoria al crear o cambiar nacionalidad."""
    country = country_code.strip().upper()
    # ensure_country_leagues already adds this player if it is national of the
    # country. Repeating the insert here could leave two pending rows for the
    # same (league_id, player_id) pair during account registration.
    ensure_country_leagues(db, country)


def add_league_member(db: Session, league: League, username: str, role: str) -> League:
    target = db.query(Player).filter(Player.name.ilike(username.strip())).first()
    if not target or target.is_bot:
        raise HTTPException(status_code=404, detail="Jugador real no encontrado")
    if any(member.player_id == target.id for member in league.members):
        raise HTTPException(status_code=409, detail="El jugador ya participa en esta liga")
    membership = LeagueMember(league_id=league.id, player_id=target.id, role=role)
    db.add(membership)
    db.flush()
    ensure_member_rankings(db, membership)
    db.commit()
    return get_league_or_404(db, league.id)


def update_league_member_role(db: Session, league: League, player_id: int, role: str) -> League:
    if player_id == league.owner_player_id and role != "admin":
        raise HTTPException(status_code=400, detail="El creador de la liga debe conservar el rol de administrador")
    member = next((item for item in league.members if item.player_id == player_id), None)
    if not member:
        raise HTTPException(status_code=404, detail="El jugador no participa en esta liga")
    member.role = role
    db.commit()
    return get_league_or_404(db, league.id)


def remove_league_member(db: Session, league: League, player_id: int) -> None:
    if league.is_system_managed:
        raise HTTPException(status_code=403, detail="La membresía de la liga nacional es automática y obligatoria")
    if player_id == league.owner_player_id:
        raise HTTPException(status_code=400, detail="No se puede quitar al creador de la liga")
    member = next((item for item in league.members if item.player_id == player_id), None)
    if not member:
        raise HTTPException(status_code=404, detail="El jugador no participa en esta liga")
    db.delete(member)
    db.commit()


def join_public_league(db: Session, league: League, user: User) -> League:
    if not league.is_public:
        raise HTTPException(status_code=403, detail="Esta liga es privada; un administrador debe agregarte")
    player = _require_current_player(user)
    if player.is_bot:
        raise HTTPException(status_code=400, detail="Los bots no pueden participar en ligas")
    if any(member.player_id == player.id for member in league.members):
        raise HTTPException(status_code=409, detail="Ya participás en esta liga")
    membership = LeagueMember(league_id=league.id, player_id=player.id, role="member")
    db.add(membership)
    db.flush()
    ensure_member_rankings(db, membership)
    db.commit()
    return get_league_or_404(db, league.id)


def leave_public_league(db: Session, league: League, user: User) -> None:
    if league.is_system_managed:
        raise HTTPException(status_code=403, detail="No podés salir de la liga nacional de tu país")
    if not league.is_public:
        raise HTTPException(status_code=403, detail="La salida de una liga privada debe gestionarla un administrador")
    player = _require_current_player(user)
    if player.id == league.owner_player_id:
        raise HTTPException(status_code=400, detail="El creador no puede abandonar su propia liga")
    remove_league_member(db, league, player.id)


def list_player_leagues(db: Session, user: User) -> list[dict]:
    player = _require_current_player(user)
    memberships = db.query(LeagueMember).options(
        joinedload(LeagueMember.league).joinedload(League.owner),
    ).filter(LeagueMember.player_id == player.id).all()
    result = []
    for membership in memberships:
        rankings = _member_rankings_with_positions(membership.league, membership.player_id)
        result.append(
            {
                "id": membership.league.id,
                "name": membership.league.name,
                "is_public": membership.league.is_public,
                "is_system_managed": membership.league.is_system_managed,
                "has_divisions": membership.league.has_divisions,
                "max_group_size": membership.league.max_group_size,
                "owner_username": membership.league.owner.name if membership.league.owner else "Maxio",
                "member_count": len(membership.league.members),
                "role": membership.role,
                "rankings": rankings,
            }
        )
    return sorted(result, key=lambda item: item["name"].lower())


def league_standings(league: League, ranking_type: str = "general") -> list[dict]:
    if ranking_type not in RANKING_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de ranking no válido")
    rankings = []
    for membership in league.members:
        ranking = next((item for item in membership.rankings if item.ranking_type == ranking_type), None)
        if ranking is None:
            continue
        rankings.append((membership, ranking))
    ordered = sorted(rankings, key=lambda item: (
        -item[1].points, -item[1].wins, item[1].losses, item[0].player.name.lower(),
    ))
    return [
        {
            "player_id": membership.player_id,
            "username": membership.player.name,
            "role": membership.role,
            "points": ranking.points,
            "position": index,
            "division": division_for_points(ranking.points) if league.has_divisions else None,
        }
        for index, (membership, ranking) in enumerate(ordered, start=1)
    ]


def _member_rankings_with_positions(league: League, player_id: int) -> list[dict]:
    result = []
    for ranking_type in RANKING_TYPES:
        standings = league_standings(league, ranking_type)
        row = next((item for item in standings if item["player_id"] == player_id), None)
        if row:
            membership = next(item for item in league.members if item.player_id == player_id)
            ranking = next(item for item in membership.rankings if item.ranking_type == ranking_type)
            result.append({
                "ranking_type": ranking_type,
                **row,
                "is_pinned": ranking.is_pinned,
            })
    return result


def toggle_player_league_pin(db: Session, league_id: int, ranking_type: str, user: User) -> None:
    if ranking_type not in ("solo_duo", "grupo"):
        raise HTTPException(status_code=400, detail="Solo podés fijar rankings Solo/Duo o Grupos")
    player = _require_current_player(user)
    membership = db.query(LeagueMember).filter(
        LeagueMember.league_id == league_id,
        LeagueMember.player_id == player.id,
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="No participás en esta liga")
    ranking = next((item for item in membership.rankings if item.ranking_type == ranking_type), None)
    if not ranking:
        ensure_member_rankings(db, membership)
        ranking = next(item for item in membership.rankings if item.ranking_type == ranking_type)
    new_value = not ranking.is_pinned
    if new_value:
        same_rankings = db.query(LeagueRanking).join(LeagueMember).filter(
            LeagueMember.player_id == player.id,
            LeagueRanking.ranking_type == ranking_type,
        ).all()
        for same_ranking in same_rankings:
            same_ranking.is_pinned = False
    ranking.is_pinned = new_value
    db.commit()


def serialize_league(league: League) -> dict:
    return {
        "id": league.id,
        "name": league.name,
        "is_public": league.is_public,
        "is_special": league.is_special,
        "is_system_managed": league.is_system_managed,
        "has_divisions": league.has_divisions,
        "max_group_size": league.max_group_size,
        "country_code": league.country_code,
        "owner_player_id": league.owner_player_id,
        "owner_username": league.owner.name if league.owner else "Maxio",
        "members": [
            {
                "player_id": membership.player_id,
                "username": membership.player.name,
                "role": membership.role,
                "rankings": _member_rankings_with_positions(league, membership.player_id),
            }
            for membership in league.members
        ],
    }
