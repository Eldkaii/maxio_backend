# src/services/telegram_identity_service.py

from sqlalchemy.orm import Session
from typing import Optional

from src.models.telegram_identity import TelegramIdentity
from src.models.user import User


# =========================
# Query helpers
# =========================

def get_identity_by_telegram_user_id(
    db: Session,
    telegram_user_id: int
) -> Optional[TelegramIdentity]:
    """
    Devuelve la identidad activa asociada a un telegram_user_id.
    """
    return (
        db.query(TelegramIdentity)
        .filter(
            TelegramIdentity.telegram_user_id == telegram_user_id,
            TelegramIdentity.is_active.is_(True)
        )
        .first()
    )


def get_identity_by_user_id(
    db: Session,
    user_id: int
) -> Optional[TelegramIdentity]:
    """
    Devuelve la identidad asociada a un usuario del sistema.
    """
    return (
        db.query(TelegramIdentity)
        .filter(
            TelegramIdentity.user_id == user_id,
            TelegramIdentity.is_active.is_(True)
        )
        .first()
    )


# =========================
# Creation / lifecycle
# =========================

def create_identity_if_not_exists(
    db: Session,
    telegram_user_id: int,
    telegram_username: Optional[str] = None
) -> TelegramIdentity:
    """
    Crea una identidad de Telegram si no existe.
    Si ya existe, la devuelve.
    """

    identity = get_identity_by_telegram_user_id(db, telegram_user_id)
    if identity:
        # Actualizamos username si cambió
        if telegram_username and identity.telegram_username != telegram_username:
            identity.telegram_username = telegram_username
            db.commit()
            db.refresh(identity)
        return identity

    identity = TelegramIdentity(
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username,
        is_active=True
    )

    db.add(identity)
    db.commit()
    db.refresh(identity)
    return identity


# =========================
# Linking logic
# =========================

def link_identity_to_user(
    db: Session,
    identity: TelegramIdentity,
    user: User
) -> TelegramIdentity:
    """
    Vincula una identidad de Telegram a un usuario del sistema.

    Reglas:
    - La identidad no puede estar ya vinculada
    - El usuario no puede estar ya vinculado a otra identidad
    """

    if identity.user_id is not None:
        raise ValueError("Esta cuenta de Telegram ya está vinculada a un usuario.")

    user_id = _get_user_id(user)
    existing_identity = get_identity_by_user_id(db, user_id)
    if existing_identity:
        raise ValueError("Este usuario ya está vinculado a otra cuenta de Telegram.")

    identity.user_id =  user_id
    db.commit()
    db.refresh(identity)
    return identity


# =========================
# State helpers
# =========================

def is_identity_linked(identity: TelegramIdentity) -> bool:
    """
    Indica si la identidad ya está vinculada a un usuario.
    """
    return identity.user_id is not None


def deactivate_identity(
    db: Session,
    identity: TelegramIdentity
) -> TelegramIdentity:
    """
    Bloquea una identidad sin borrarla.
    """
    identity.is_active = False
    db.commit()
    db.refresh(identity)
    return identity

def _get_user_id(user) -> int:
    # Caso dict-like
    if isinstance(user, dict):
        if "id" in user:
            return user["id"]

    # Caso objeto con atributo
    if hasattr(user, "id"):
        return user.id

    raise ValueError(
        f"No se pudo obtener user.id. Tipo recibido: {type(user)}"
    )