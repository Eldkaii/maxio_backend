from typing import Optional
from sqlalchemy import Float

from pydantic import BaseModel, Field, ConfigDict

class PlayerStatsUpdate(BaseModel):
    tiro: Optional[float] = None
    ritmo: Optional[float] = None
    fisico: Optional[float] = None
    defensa: Optional[float] = None
    aura: Optional[float] = None


class CustomBotCreate(BaseModel):
    """Datos de un bot diseñado desde el creador de partidos."""
    name: str = Field(min_length=2, max_length=100)
    tiro: float = Field(default=50, ge=0, le=100)
    ritmo: float = Field(default=50, ge=0, le=100)
    fisico: float = Field(default=50, ge=0, le=100)
    defensa: float = Field(default=50, ge=0, le=100)
    aura: float = Field(default=5, ge=0, le=10)



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


