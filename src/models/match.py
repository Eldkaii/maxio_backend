from sqlalchemy import Column, Integer, DateTime, func, ForeignKey, Enum
from sqlalchemy.orm import relationship
from src.database import Base
import enum

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=func.now(), nullable=False)
    max_players = Column(Integer, default=10, nullable=False)

    team1_id = Column(
        Integer,
        ForeignKey("teams.id", name="fk_matches_team1_id", use_alter=True),
    )

    team2_id = Column(
        Integer,
        ForeignKey("teams.id", name="fk_matches_team2_id", use_alter=True),
    )

    winner_team_id = Column(
        Integer,
        ForeignKey("teams.id", name="fk_matches_winner_team_id", use_alter=True),
        nullable=True
    )

    team1 = relationship("Team", foreign_keys=[team1_id])
    team2 = relationship("Team", foreign_keys=[team2_id])
    winner_team = relationship("Team", foreign_keys=[winner_team_id])


    players = relationship("Player", secondary="match_players", back_populates="matches", overlaps="match_associations")
    match_associations = relationship("MatchPlayer", back_populates="match", cascade="all, delete-orphan")


class TeamEnum(enum.Enum):
    team1 = "team1"
    team2 = "team2"

class MatchPlayer(Base):
    __tablename__ = "match_players"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"))
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"))
    team = Column(Enum(TeamEnum), nullable=True)

    match = relationship("Match", back_populates="match_associations", overlaps="players,matches")
    player = relationship("Player", back_populates="match_associations", overlaps="matches,players")



