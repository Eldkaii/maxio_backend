from pydantic import BaseModel
from pydantic import ConfigDict
from typing import List, Dict, Literal


# ---------------------
# Submodelos
# ---------------------
class PlayerStats(BaseModel):
    tiro: float
    ritmo: float
    fisico: float
    defensa: float
    aura: float
    elo: int

    class Config:
        model_config = ConfigDict(from_attributes=True)


class MatchesSummary(BaseModel):
    played: int
    won: int
    winrate: float
    recent_results: List[bool]

    class Config:
        model_config = ConfigDict(from_attributes=True)


class MatchInfoPlayer(BaseModel):
    name: str


class RecentMatchInfo(BaseModel):
    match_id: int
    date: str  # ISO
    team: Literal["team1", "team2"]
    result: Literal["win", "loss", "pending"]
    teammates: List[MatchInfoPlayer]
    opponents: List[MatchInfoPlayer]

    class Config:
        model_config = ConfigDict(from_attributes=True)


class RelationsInfo(BaseModel):
    most_played_with: List[MatchInfoPlayer]
    top_allies: List[MatchInfoPlayer]
    top_opponents: List[MatchInfoPlayer]

    class Config:
        model_config = ConfigDict(from_attributes=True)


class EvaluationInfo(BaseModel):
    can_evaluate: List[str]  # lista de nombres de jugadores que puede evaluar

    class Config:
        model_config = ConfigDict(from_attributes=True)


# ---------------------
# Schema principal
# ---------------------
class FullPlayerInfo(BaseModel):
    id: int
    name: str
    cant_partidos: int
    is_bot: bool

    stats: PlayerStats
    matches_summary: MatchesSummary
    recent_matches: List[RecentMatchInfo]
    relations: RelationsInfo
    evaluation: EvaluationInfo

    class Config:
        model_config = ConfigDict(from_attributes=True)
