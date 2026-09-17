from src.schemas.match_schema import MatchReportResponse, TeamBalanceReport, PlayerStat
from src.models import Match, Player
from typing import List, Dict

def build_individual_stats(players: List[Player]) -> List[PlayerStat]:
    return [
        PlayerStat(
            name=player.name,
            photo_path=player.photo_path,
            stats={
                "tiro": player.tiro,
                "ritmo": player.ritmo,
                "defensa": player.defensa,
                "fisico": player.fisico,
                "aura": player.aura,
            },
        )
        for player in players
    ]
