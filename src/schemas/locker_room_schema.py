from pydantic import BaseModel, Field
from src.schemas.avatar_schema import AvatarItem


class LockerRoomInfo(BaseModel):
    equipment: list[AvatarItem] = Field(default_factory=list)
