from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# Para crear un nuevo Match (input del cliente)
class MatchCreate(BaseModel):
    date: Optional[datetime] = Field(default_factory=datetime.utcnow)
    max_players: int = 10  # Valor por defecto

    class Config:
        orm_mode = True


class PlayerResponse(BaseModel):
    id: int
    username: str = Field(..., alias="name")

    class Config:
        orm_mode = True

class TeamResponse(BaseModel):
    id: int
    name: str
    players: List[PlayerResponse]

    class Config:
        orm_mode = True

class MatchResponse(BaseModel):
    id: int
    date: datetime
    max_players: int
    team1: Optional[TeamResponse]
    team2: Optional[TeamResponse]
    winner_team: Optional[TeamResponse]  # nuevo campo


    class Config:
        orm_mode = True
