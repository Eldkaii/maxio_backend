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
    # Cantidad de partidos compartidos, según la sección de relaciones.
    # Son opcionales porque también se reutiliza para los jugadores de un
    # partido reciente, donde esos contadores no se envían.
    games_together: int | None = None
    games_apart: int | None = None
    total_games: int | None = None
    # Resultado declarado por este jugador para el partido.
    response: Literal["win", "loss", "pending", "bot"] | None = None


class RecentMatchInfo(BaseModel):
    match_id: int
    date: str  # ISO
    # Un partido recién creado o cuyo balanceo falló puede todavía no tener
    # equipo asignado para este jugador.
    team: Literal["team1", "team2"] | None = None
    result: Literal["win", "loss", "pending"]
    # Respuesta del jugador cuyo perfil se está consultando.
    my_response: Literal["win", "loss", "pending", "bot"] | None = None
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
    can_evaluate: List[MatchInfoPlayer]  # jugadores que puede evaluar

    class Config:
        model_config = ConfigDict(from_attributes=True)


# ---------------------
# Schema principal
# ---------------------
class FullPlayerInfo(BaseModel):
    id: int
    name: str
    first_name: str = ""
    last_name: str = ""
    nationality: str = "UY"
    cant_partidos: int
    is_bot: bool
    photo_path: str | None = None

    stats: PlayerStats
    matches_summary: MatchesSummary
    recent_matches: List[RecentMatchInfo]
    relations: RelationsInfo
    evaluation: EvaluationInfo

    class Config:
        model_config = ConfigDict(from_attributes=True)
