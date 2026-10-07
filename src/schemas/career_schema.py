from pydantic import BaseModel, Field
from typing import Literal


class CareerMilestone(BaseModel):
    key: str
    name: str
    metric: str
    progress: int
    target: int
    earned: bool
    reward: str
    peer: str | None = None
    trophy_image: str | None = None
    reward_type: Literal["achievement", "trophy"] = "achievement"
    earned_at: str | None = None
    conditions: dict[str, float] = Field(default_factory=dict)
    family: str | None = None


class CareerConnection(BaseModel):
    kind: str
    peer: str | None = None
    count: int
    title: str
    next_name: str
    target: int
    complete: bool


class CareerInfo(BaseModel):
    title: str
    stage: int
    neighborhood: str
    description: str
    played: int
    milestones: list[CareerMilestone]
    connections: list[CareerConnection]
    next_milestone: CareerMilestone | None = None
    earned_count: int
