# src/schemas/user_schema.py

from pydantic import BaseModel, EmailStr, constr, ConfigDict, Field
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
    is_admin: bool = False

    model_config = ConfigDict(from_attributes=True)


class AdminPlayerCreate(BaseModel):
    """Datos de alta de un jugador humano desde la consola global."""

    username: constr(min_length=3, max_length=50)
    first_name: str = ""
    last_name: str = ""
    nationality: constr(min_length=2, max_length=2) = "UY"
    email: EmailStr
    password: constr(min_length=6)
    tiro: float = Field(default=50, ge=0, le=100)
    ritmo: float = Field(default=50, ge=0, le=100)
    fisico: float = Field(default=50, ge=0, le=100)
    defensa: float = Field(default=50, ge=0, le=100)
    aura: float = Field(default=50, ge=0, le=100)

    def stats(self) -> Dict[str, float]:
        return {
            "tiro": self.tiro,
            "ritmo": self.ritmo,
            "fisico": self.fisico,
            "defensa": self.defensa,
            "aura": self.aura,
        }

