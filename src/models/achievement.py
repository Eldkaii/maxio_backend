from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship

from src.database import Base


class AchievementDefinition(Base):
    __tablename__ = "achievement_definitions"

    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=False, default="")
    conditions = Column(JSON, nullable=False, default=dict)
    trophy_image = Column(String(255), nullable=True)
    reward_type = Column(String(16), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    awards = relationship("AchievementAward", back_populates="achievement", cascade="all, delete-orphan")


class AchievementAward(Base):
    __tablename__ = "achievement_awards"
    __table_args__ = (UniqueConstraint("achievement_id", "player_id", name="uq_achievement_player"),)

    id = Column(Integer, primary_key=True)
    achievement_id = Column(Integer, ForeignKey("achievement_definitions.id", ondelete="CASCADE"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    progress = Column(Integer, nullable=False, default=0)
    achievement = relationship("AchievementDefinition", back_populates="awards")
