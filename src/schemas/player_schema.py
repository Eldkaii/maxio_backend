from typing import Optional
from sqlalchemy import Float

from pydantic import BaseModel, Field, ConfigDict

class PlayerStatsUpdate(BaseModel):
    punteria: Optional[float] = None
    velocidad: Optional[float] = None
    dribbling: Optional[float] = None
    defensa: Optional[float] = None
    magia: Optional[float] = None



class PlayerResponse(BaseModel):
    id: int
    name: str
    cant_partidos: int
    elo: float
    punteria: float
    velocidad: float
    dribbling: float
    defensa: float
    magia: float

    class Config:
        model_config = ConfigDict(from_attributes=True)  # reemplaza orm_mode=True

class RelatedPlayerResponse(PlayerResponse):
    games: int  # puede representar partidos totales, juntos o en contra