# src/schemas/user_schema.py

from pydantic import BaseModel, EmailStr, constr, ConfigDict
from typing import Optional, Dict

class UserCreate(BaseModel):
    username: constr(min_length=3, max_length=50)
    first_name: str = ""
    last_name: str = ""
    nationality: constr(min_length=2, max_length=2) = "UY"
    email: EmailStr
    password: constr(min_length=6)
    stats: Optional[Dict[str, int]] = None  # Ejemplo: {"accuracy": 5, "speed": 3}
    is_bot:Optional[bool]


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    nationality: str = "UY"

    class Config:
        model_config = ConfigDict(from_attributes=True)  # reemplaza orm_mode=True

