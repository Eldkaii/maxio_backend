from typing import List, Tuple
from itertools import combinations
from collections import defaultdict
from src.models.player import Player, PlayerRelation
from itertools import combinations
from sqlalchemy.sql import text

from src.utils.logger_config import app_logger as logger


STAT_NAMES = ["punteria", "velocidad", "dribbling", "defensa", "magia"]



def player_total_stats(player: Player) -> int:
    return sum(getattr(player, stat) for stat in STAT_NAMES)


def player_stats_breakdown(player: Player) -> dict:
    return {stat: getattr(player, stat) for stat in STAT_NAMES}


def team_stats_summary(team: List[Player]) -> dict:
    summary = defaultdict(int)
    for player in team:
        for stat, value in player_stats_breakdown(player).items():
            summary[stat] += value
    return dict(summary)


def team_total_stats(team: List[Player]) -> int:
    return sum(player_total_stats(p) for p in team)


def team_stat_variance(team1: List[Player], team2: List[Player]) -> float:
    """Devuelve la suma de diferencias absolutas por stat."""
    s1 = team_stats_summary(team1)
    s2 = team_stats_summary(team2)
    return sum(abs(s1[stat] - s2[stat]) for stat in STAT_NAMES)


def chemistry_score(team: List[Player]) -> int:
    """Suma la química de todos los pares en un equipo."""
    score = 0
    for i, p1 in enumerate(team):
        for p2 in team[i+1:]:
            rel = p1.get_relation_with(p2.id)
            if rel:
                score += rel.games_together - rel.games_apart
    return score


def flatten_groups(groups: List[List[Player]]) -> List[Player]:
    return [p for group in groups for p in group]


def is_group_preserved(group: List[Player], team: List[Player]) -> bool:
    return all(p in team for p in group) or all(p not in team for p in group)


def all_groups_preserved(groups: List[List[Player]], team1: List[Player], team2: List[Player]) -> bool:
    return all(is_group_preserved(group, team1) or is_group_preserved(group, team2) for group in groups)

def calculate_balance_score(team1: List[Player], team2: List[Player]) -> float:
    """
    Supongmos:
        Equipo 1 suma 300 puntos de stats totales.
        Equipo 2 suma 310.
        La varianza por stat es 14 (ej: 2 de diferencia en puntería, 4 en defensa, etc).
        Entonces el balance score sería:

        abs(300 - 310) + 14 = 10 + 14 = 24
        Un enfrentamiento ideal tendría un balance_score cercano a 0.
    """
    total_diff = abs(team_total_stats(team1) - team_total_stats(team2))
    stat_variance = team_stat_variance(team1, team2)
    return total_diff + stat_variance

def calculate_stat_diff(team1: List[Player], team2: List[Player]) -> dict:
    """
    Calcula la diferencia absoluta por stat entre dos equipos.
    Devuelve un diccionario con cada stat y su diferencia.
    """
    stats1 = team_stats_summary(team1)
    stats2 = team_stats_summary(team2)
    return {stat: abs(stats1[stat] - stats2[stat]) for stat in STAT_NAMES}

def balance_teams(groups: List[List[Player]]) -> Tuple[List[Player], List[Player]]:
    """Balancea equipos sin romper grupos prearmados."""

    prearmados = [g for g in groups if len(g) > 1]
    if len(prearmados) > 2:
        raise ValueError("No se permiten más de 2 grupos prearmados.")

    players = flatten_groups(groups)
    n = len(players)
    if n % 2 != 0:
        raise ValueError("Debe haber un número par de jugadores.")

    half = n // 2
    best_score = float("inf")
    best_combo = None

    # Generar combinaciones de grupos completos cuya suma de jugadores sea igual a n/2
    combination_count = 0
    for r in range(1, len(groups)):
        for group_combo in combinations(groups, r):
            combination_count += 1
            team1 = flatten_groups(group_combo)
            if len(team1) != half:
                continue  # tamaño incorrecto

            team2 = [p for p in players if p not in team1]

            # Aseguramos que no se rompa ningún grupo original
            if not all_groups_preserved(groups, team1, team2):
                continue

            stats1 = team_stats_summary(team1)
            stats2 = team_stats_summary(team2)
            total_diff = sum(abs(stats1[s] - stats2[s]) for s in STAT_NAMES)

            chem_score = chemistry_score(team1) + chemistry_score(team2)

            group_bonus = 5 * sum(
                1 for g in groups if is_group_preserved(g, team1)
            )

            score = total_diff - chem_score - group_bonus

            if score < best_score:
                best_score = score
                best_combo = (team1, team2)

    logger.info(f"Intentadas {combination_count} combinaciones")

    if best_combo:
        return best_combo

    raise RuntimeError("No se pudo generar una combinación balanceada de equipos.")