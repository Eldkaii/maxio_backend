from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from src.models import League, LeagueMember, Player, User


COUNTRY_LEAGUE_NAMES = {"UY": "UY 🇺🇾"}
COUNTRY_LEAGUE_TYPES = ("solo_duo", "grupo")


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
    league_type: str,
    is_public: bool = False,
    is_special: bool = False,
) -> League:
    owner = _require_current_player(user)
    if not user.is_admin:
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

    league = League(
        name=normalized_name,
        league_type=league_type,
        is_public=is_public,
        is_special=is_special,
        owner_player_id=owner.id,
    )
    db.add(league)
    db.flush()
    db.add(LeagueMember(league_id=league.id, player_id=owner.id, role="admin"))
    db.commit()
    return get_league_or_404(db, league.id)


def ensure_country_leagues(db: Session, country_code: str) -> list[League]:
    """Crea y sincroniza las ligas públicas obligatorias de un país soportado."""
    country = country_code.strip().upper()
    league_name = COUNTRY_LEAGUE_NAMES.get(country)
    if not league_name:
        return []
    leagues = []
    for league_type in COUNTRY_LEAGUE_TYPES:
        league = db.query(League).filter(
            League.country_code == country,
            League.league_type == league_type,
        ).first()
        if not league:
            league = League(
                name=league_name,
                league_type=league_type,
                is_public=True,
                is_special=True,
                is_system_managed=True,
                country_code=country,
            )
            db.add(league)
            db.flush()
        else:
            # Normaliza la liga nacional creada por versiones anteriores.
            league.name = league_name
            league.is_public = True
            league.is_special = True
            league.is_system_managed = True
        leagues.append(league)
    players = db.query(Player).join(User, Player.user_id == User.id).filter(
        Player.is_bot.is_(False),
        User.nationality == country,
    ).all()
    for league in leagues:
        joined_ids = {member.player_id for member in league.members}
        for player in players:
            if player.id not in joined_ids:
                db.add(LeagueMember(league_id=league.id, player_id=player.id, role="member"))
    db.flush()
    return leagues


def sync_player_country_league(db: Session, player: Player, country_code: str) -> None:
    """Mantiene la inscripción obligatoria al crear o cambiar nacionalidad."""
    country = country_code.strip().upper()
    leagues = ensure_country_leagues(db, country)
    national_leagues = db.query(League).filter(League.is_system_managed.is_(True)).all()
    for national_league in national_leagues:
        membership = next((item for item in national_league.members if item.player_id == player.id), None)
        if national_league in leagues:
            if not membership:
                db.add(LeagueMember(league_id=national_league.id, player_id=player.id, role="member"))
        elif membership:
            db.delete(membership)


def add_league_member(db: Session, league: League, username: str, role: str) -> League:
    target = db.query(Player).filter(Player.name.ilike(username.strip())).first()
    if not target or target.is_bot:
        raise HTTPException(status_code=404, detail="Jugador real no encontrado")
    if any(member.player_id == target.id for member in league.members):
        raise HTTPException(status_code=409, detail="El jugador ya participa en esta liga")
    db.add(LeagueMember(league_id=league.id, player_id=target.id, role=role))
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
    db.add(LeagueMember(league_id=league.id, player_id=player.id, role="member"))
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
        standings = league_standings(membership.league)
        position = next(row["position"] for row in standings if row["player_id"] == player.id)
        result.append(
            {
                "id": membership.league.id,
                "name": membership.league.name,
                "league_type": membership.league.league_type,
                "is_public": membership.league.is_public,
                "is_system_managed": membership.league.is_system_managed,
                "owner_username": membership.league.owner.name if membership.league.owner else "Maxio",
                "member_count": len(membership.league.members),
                "role": membership.role,
                "is_pinned": membership.is_pinned,
                "points": membership.points,
                "position": position,
            }
        )
    return sorted(result, key=lambda item: (not item["is_pinned"], item["name"].lower(), item["league_type"]))


def league_standings(league: League) -> list[dict]:
    ordered = sorted(
        league.members,
        key=lambda item: (-item.points, -item.wins, item.losses, item.player.name.lower()),
    )
    return [
        {
            "player_id": membership.player_id,
            "username": membership.player.name,
            "role": membership.role,
            "points": membership.points,
            "position": index,
        }
        for index, membership in enumerate(ordered, start=1)
    ]


def toggle_player_league_pin(db: Session, league_id: int, user: User) -> None:
    player = _require_current_player(user)
    membership = db.query(LeagueMember).filter(
        LeagueMember.league_id == league_id,
        LeagueMember.player_id == player.id,
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="No participás en esta liga")
    new_value = not membership.is_pinned
    if new_value:
        # Cada modalidad tiene su propia liga destacada: fijar una de Grupo
        # no desplaza la elegida en Solo/Duo, ni viceversa.
        same_type_memberships = db.query(LeagueMember).join(League).filter(
            LeagueMember.player_id == player.id,
            League.league_type == membership.league.league_type,
        ).all()
        for same_type_membership in same_type_memberships:
            same_type_membership.is_pinned = False
    membership.is_pinned = new_value
    db.commit()


def serialize_league(league: League) -> dict:
    return {
        "id": league.id,
        "name": league.name,
        "league_type": league.league_type,
        "is_public": league.is_public,
        "is_special": league.is_special,
        "is_system_managed": league.is_system_managed,
        "country_code": league.country_code,
        "owner_player_id": league.owner_player_id,
        "owner_username": league.owner.name if league.owner else "Maxio",
        "members": league_standings(league),
    }
