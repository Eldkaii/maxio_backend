"""Validated, versioned configuration for the layered player avatar."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AvatarEquipment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jersey: str = Field(default="training", max_length=32)
    shorts: str = Field(default="basic", max_length=32)
    boots: str = Field(default="classic", max_length=32)
    cap: str = Field(default="none", max_length=32)
    tattoo: str = Field(default="none", max_length=32)


class AvatarConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    build: Literal["slim", "regular", "broad"] = "regular"
    skin: Literal["porcelain", "sand", "olive", "copper", "brown", "deep"] = "olive"
    hair: Literal["short", "curls", "tied", "shaved"] = "short"
    hair_color: Literal["dark", "brown", "blond", "red", "grey"] = "dark"
    beard: Literal["none", "short"] = "none"
    equipment: AvatarEquipment = Field(default_factory=AvatarEquipment)


class AvatarVisual(BaseModel):
    config: AvatarConfig = Field(default_factory=AvatarConfig)
    face_url: str | None = None


class AvatarItem(BaseModel):
    slot: str
    id: str
    name: str
    requirement: str
    unlocked: bool
    progress: int
    target: int


class AvatarWardrobe(AvatarVisual):
    catalog: list[AvatarItem] = Field(default_factory=list)
