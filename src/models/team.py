# src/models/team.py

from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from src.database import Base

# Tabla intermedia: relaciona jugadores con equipos
team_players = Table(
    "team_players",
    Base.metadata,
    Column("team_id", Integer, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
    Column("player_id", Integer, ForeignKey("players.id", ondelete="CASCADE"), primary_key=True)
)

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)  # Opcional, podés usar "Team A", "Team B", etc.
    match_id = Column(
        Integer,
        ForeignKey("matches.id", name="fk_teams_match_id", use_alter=True),
    )

    players = relationship("Player", secondary=team_players, backref="teams")
    match = relationship("Match", foreign_keys=[match_id], backref="teams")
