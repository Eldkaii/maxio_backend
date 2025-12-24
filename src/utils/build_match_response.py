from src.schemas.match_schema import MatchReportResponse, TeamBalanceReport, PlayerStat
from src.models import Match, Player
from typing import List, Dict

def build_individual_stats(players: List[Player]) -> List[PlayerStat]:
    return [
        PlayerStat(
            name=player.name,
            stats={
                "punteria": player.punteria,
                "velocidad": player.velocidad,
                "defensa": player.defensa,
                "resistencia": player.resistencia,
                "magia": player.magia,
            },
        )
        for player in players
    ]