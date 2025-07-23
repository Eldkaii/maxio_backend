from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

class PlayerStatsUpdate(BaseModel):
    punteria: Optional[int] = None
    velocidad: Optional[int] = None
    dribbling: Optional[int] = None
    defensa: Optional[int] = None
    magia: Optional[int] = None



class PlayerResponse(BaseModel):
    id: int
    name: str
    cant_partidos: int
    elo: int
    punteria: int
    velocidad: int
    dribbling: int
    defensa: int
    magia: int

    class Config:
        model_config = ConfigDict(from_attributes=True)  # reemplaza orm_mode=True

class RelatedPlayerResponse(PlayerResponse):
    games: int  # puede representar partidos totales, juntos o en contra