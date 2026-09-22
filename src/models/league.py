from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.database import Base


class League(Base):
    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    # Valores admitidos: solo_duo y grupo. Se mantiene como texto para no
    # introducir tipos ENUM nuevos en instalaciones PostgreSQL existentes.
    league_type = Column(String(16), nullable=False)
    is_public = Column(Boolean, nullable=False, default=False)
    # Las ligas especiales solo pueden ser creadas por un administrador global.
    is_special = Column(Boolean, nullable=False, default=False)
    # Las ligas nacionales son públicas pero gestionadas por la plataforma.
    is_system_managed = Column(Boolean, nullable=False, default=False)
    country_code = Column(String(2), nullable=True)
    owner_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)

    owner = relationship("Player", foreign_keys=[owner_player_id], back_populates="owned_leagues")
    members = relationship("LeagueMember", back_populates="league", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="league")

    __table_args__ = (
        UniqueConstraint("country_code", "league_type", name="uq_league_country_type"),
    )


class LeagueMember(Base):
    __tablename__ = "league_members"
    __table_args__ = (
        UniqueConstraint("league_id", "player_id", name="uq_league_member"),
    )

    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    # member participa y admin puede crear partidos puntuables y administrar la liga.
    role = Column(String(16), nullable=False, default="member")
    is_pinned = Column(Boolean, nullable=False, default=False)
    points = Column(Integer, nullable=False, default=0)
    matches_played = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)

    league = relationship("League", back_populates="members")
    player = relationship("Player", back_populates="league_memberships")
