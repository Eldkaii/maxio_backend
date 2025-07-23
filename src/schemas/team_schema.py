from pydantic import BaseModel
from typing import List

class PlayerResponse(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True

class TeamResponse(BaseModel):
    id: int
    name: str
    players: List[PlayerResponse]

    class Config:
        orm_mode = True
