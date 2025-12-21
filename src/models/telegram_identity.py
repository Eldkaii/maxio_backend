from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import Base


class TelegramIdentity(Base):
    __tablename__ = "telegram_identities"

    id = Column(Integer, primary_key=True, index=True)

    # ID único que Telegram asigna a cada usuario
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Username de Telegram (puede ser None o cambiar con el tiempo)
    telegram_username = Column(String(100), nullable=True)

    # Relación con el usuario del sistema (Player/User)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        unique=True
    )

    # Permite bloquear el acceso sin borrar el registro
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relación ORM
    user = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<TelegramIdentity "
            f"telegram_user_id={self.telegram_user_id} "
            f"user_id={self.user_id} "
            f"is_active={self.is_active}>"
        )
