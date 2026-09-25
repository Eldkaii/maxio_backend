from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.models import League, LeagueMember, Match, Player, User
from src.schemas.user_schema import AdminPlayerCreate, UserCreate
from src.services.user_service import create_user
from src.utils.logger_config import app_logger as logger


GLOBAL_ADMIN_USERNAME = "admin"
GLOBAL_ADMIN_EMAIL = "admin@maxio.local"
# This is only used to bootstrap a missing local administrator.  The password
# is hashed before persistence and is never returned by the API or logs.
GLOBAL_ADMIN_PASSWORD = "maxioadmin"


def ensure_global_admin(db: Session) -> User:
    """Create the bootstrap administrator without a competitive player profile.

    Existing accounts are never converted by deleting their player or match
    history.  A pre-existing account named ``admin`` is promoted only when it
    already has no player profile; otherwise the operator must resolve that
    legacy account explicitly.
    """
    existing = db.query(User).filter(
        func.lower(User.username) == GLOBAL_ADMIN_USERNAME
    ).first()
    if existing:
        if existing.player:
            logger.warning("La cuenta admin existente tiene un perfil de jugador y no fue convertida automáticamente")
            return existing
        if not existing.is_admin:
            existing.is_admin = True
            db.commit()
        return existing

    user = User(
        username=GLOBAL_ADMIN_USERNAME,
        first_name="Maxio",
        last_name="Admin",
        nationality="UY",
        email=GLOBAL_ADMIN_EMAIL,
        password="",
        # Legacy schema keeps this column mandatory.  Do not store a plaintext
        # password in it for the administrator.
        password_test="",
        is_admin=True,
    )
    user.set_password(GLOBAL_ADMIN_PASSWORD)
    user.password_test = ""
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Administrador global inicial creado sin perfil de jugador")
    return user


def require_global_admin(user: User) -> User:
    if not user.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Solo el administrador global puede realizar esta acción")
    return user


def create_player_as_admin(db: Session, payload: AdminPlayerCreate) -> User:
    """Create a normal human account and its player profile from the admin UI."""
    user_data = UserCreate(
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        nationality=payload.nationality,
        email=payload.email,
        password=payload.password,
        stats=payload.stats(),
        is_bot=False,
    )
    return create_user(user_data, db, stats=user_data.stats)


def get_admin_summary(db: Session) -> dict[str, int]:
    """Return operational metrics without exposing the admin as a player."""
    real_players = db.query(Player).outerjoin(User, Player.user_id == User.id).filter(
        Player.is_bot.is_(False),
        or_(User.id.is_(None), User.is_admin.is_(False)),
    ).count()
    return {
        "real_players": real_players,
        "bots": db.query(Player).filter(Player.is_bot.is_(True)).count(),
        "leagues": db.query(League).count(),
        "league_memberships": db.query(LeagueMember).count(),
        "matches": db.query(Match).count(),
        "upcoming_matches": db.query(Match).filter(Match.date >= datetime.utcnow()).count(),
    }
