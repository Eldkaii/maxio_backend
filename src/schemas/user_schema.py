# src/schemas/user_schema.py

from pydantic import BaseModel, EmailStr, constr, ConfigDict
from typing import Optional, Dict

class UserCreate(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    password: constr(min_length=6)
    stats: Optional[Dict[str, int]] = None  # Ejemplo: {"accuracy": 5, "speed": 3}
    is_bot:Optional[bool]


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        model_config = ConfigDict(from_attributes=True)  # reemplaza orm_mode=True

