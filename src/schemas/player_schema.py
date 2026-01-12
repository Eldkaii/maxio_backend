from typing import Optional
from sqlalchemy import Float

from pydantic import BaseModel, Field, ConfigDict

class PlayerStatsUpdate(BaseModel):
    tiro: Optional[float] = None
    ritmo: Optional[float] = None
    fisico: Optional[float] = None
    defensa: Optional[float] = None
    aura: Optional[float] = None



class PlayerResponse(BaseModel):
    id: int
    name: str
    cant_partidos: int
    elo: float
    tiro: float
    ritmo: float
    fisico: float
    defensa: float
    aura: float

    class Config:
        model_config = ConfigDict(from_attributes=True)  # reemplaza orm_mode=True

class RelatedPlayerResponse(PlayerResponse):
    games: int  # puede representar partidos totales, juntos o en contra


