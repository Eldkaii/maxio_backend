from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


RankingType = Literal["general", "solo_duo", "grupo"]
LeagueRole = Literal["member", "admin"]


class LeagueCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    is_public: bool = False
    is_special: bool = False
    max_group_size: Optional[int] = Field(default=None, ge=2, le=5)


class LeagueMemberCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    role: LeagueRole = "member"


class LeagueMemberRoleUpdate(BaseModel):
    role: LeagueRole


class RankingResponse(BaseModel):
    ranking_type: RankingType
    points: int
    position: int
    division: Optional[str] = None


class LeagueMemberResponse(BaseModel):
    player_id: int
    username: str
    role: LeagueRole
    rankings: list[RankingResponse]


class MyLeagueResponse(BaseModel):
    id: int
    name: str
    is_public: bool
    is_system_managed: bool
    has_divisions: bool
    owner_username: str
    member_count: int
    role: LeagueRole
    max_group_size: Optional[int]
    rankings: list[RankingResponse]


class LeagueResponse(BaseModel):
    id: int
    name: str
    is_public: bool
    is_special: bool
    is_system_managed: bool
    has_divisions: bool
    max_group_size: Optional[int]
    country_code: Optional[str]
    owner_player_id: Optional[int]
    owner_username: str
    members: list[LeagueMemberResponse]

    model_config = ConfigDict(from_attributes=True)
