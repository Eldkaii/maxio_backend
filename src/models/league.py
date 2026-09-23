from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.database import Base


class League(Base):
    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    # Campo legado de la primera versión. La modalidad pertenece ahora a cada
    # ranking de la liga, no a la liga; se conserva para migrar instalaciones
    # existentes y queda vacío en las ligas nuevas.
    league_type = Column(String(16), nullable=True)
    is_public = Column(Boolean, nullable=False, default=False)
    # Las ligas especiales solo pueden ser creadas por un administrador global.
    is_special = Column(Boolean, nullable=False, default=False)
    # Las ligas nacionales son públicas pero gestionadas por la plataforma.
    is_system_managed = Column(Boolean, nullable=False, default=False)
    has_divisions = Column(Boolean, nullable=False, default=False)
    # None permite grupos de cualquier tamaño; 2 limita la liga a Solo/Duo.
    max_group_size = Column(Integer, nullable=True)
    country_code = Column(String(2), nullable=True)
    owner_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)

    owner = relationship("Player", foreign_keys=[owner_player_id], back_populates="owned_leagues")
    members = relationship("LeagueMember", back_populates="league", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="league")


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
    win_streak = Column(Integer, nullable=False, default=0)

    rankings = relationship("LeagueRanking", back_populates="member", cascade="all, delete-orphan")

    league = relationship("League", back_populates="members")
    player = relationship("Player", back_populates="league_memberships")


class LeagueRanking(Base):
    __tablename__ = "league_rankings"
    __table_args__ = (UniqueConstraint("league_member_id", "ranking_type", name="uq_league_member_ranking"),)

    id = Column(Integer, primary_key=True)
    league_member_id = Column(Integer, ForeignKey("league_members.id", ondelete="CASCADE"), nullable=False)
    # general, solo_duo o grupo
    ranking_type = Column(String(16), nullable=False)
    points = Column(Integer, nullable=False, default=0)
    matches_played = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    win_streak = Column(Integer, nullable=False, default=0)
    is_pinned = Column(Boolean, nullable=False, default=False)

    member = relationship("LeagueMember", back_populates="rankings")
