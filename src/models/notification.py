
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON, func
)

from sqlalchemy.orm import relationship
from src.database import Base
from datetime import datetime

from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY  # Solo si usás PostgreSQL

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    event_type = Column(String, nullable=False)
    channel = Column(String, nullable=False)  # telegram, email, etc
    status = Column(String, default="pending")

    payload = Column(JSON, nullable=False)

    attempts = Column(Integer, default=0)

    available_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    sent_at = Column(DateTime, nullable=True)

    user = relationship("User", lazy="joined")
