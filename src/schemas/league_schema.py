from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


LeagueType = Literal["solo_duo", "grupo"]
LeagueRole = Literal["member", "admin"]


class LeagueCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    league_type: LeagueType
    is_public: bool = False
    is_special: bool = False


class LeagueMemberCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    role: LeagueRole = "member"


class LeagueMemberRoleUpdate(BaseModel):
    role: LeagueRole


class LeagueMemberResponse(BaseModel):
    player_id: int
    username: str
    role: LeagueRole
    points: int
    position: int


class MyLeagueResponse(BaseModel):
    id: int
    name: str
    league_type: LeagueType
    is_public: bool
    is_system_managed: bool
    owner_username: str
    member_count: int
    role: LeagueRole
    is_pinned: bool
    points: int
    position: int


class LeagueResponse(BaseModel):
    id: int
    name: str
    league_type: LeagueType
    is_public: bool
    is_special: bool
    is_system_managed: bool
    country_code: Optional[str]
    owner_player_id: Optional[int]
    owner_username: str
    members: list[LeagueMemberResponse]

    model_config = ConfigDict(from_attributes=True)
