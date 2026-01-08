from sqlalchemy.orm import Session

from src.models.user import User
from src.services.player_service import create_player_for_user
from typing import Optional, Dict


from src.schemas.user_schema import UserCreate
from src.utils.logger_config import app_logger as logger
import bcrypt

def create_user(
    user_data: UserCreate,
    db: Session,
    stats: Optional[Dict[str, int]] = None
) -> User:

    existing = db.query(User).filter(
        (User.email == user_data.email) |
        (User.username == user_data.username)
    ).first()

    if existing:
        raise ValueError("El email o el username ya están registrados")

    hashed_password = bcrypt.hashpw(
        user_data.password.encode("utf-8"),
        bcrypt.gensalt()
    )

    new_user = User(
        username=user_data.username,
        password=hashed_password.decode("utf-8"),
        password_test=user_data.password,
        email=user_data.email
    )

    db.add(new_user)
    db.flush()  # 👈 CLAVE

    create_player_for_user(
        user=new_user,
        db=db,
        stats=stats,
        is_bot=user_data.is_bot
    )

    db.commit()
    db.refresh(new_user)

    logger.info(f"Usuario creado: {new_user.username}")

    return new_user


