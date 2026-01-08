
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON, func,
    UniqueConstraint
)

from src.database import Base

class MatchResultReply(Base):
    __tablename__ = "match_result_replies"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    result = Column(String, nullable=False)  # "win" | "loss"

    replied_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("match_id", "user_id"),
    )
