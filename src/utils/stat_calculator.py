# src/utils/stat_calculator.py
from src.models import Player

def calculate_updated_stats(
    current_stats: dict[str, int],
    evaluator_stats: dict[str, int],
    incoming_stats: dict[str, int],
    elo: int
) -> dict[str, int]:
    updated_stats = {}

    # Escalar el ELO a un factor de ajuste entre -1.0 y 1.0
    elo_scale = max(-1000, min(1000, elo)) / 1000

    # Iterar SOLO sobre los stats que vienen en la evaluación
    for stat, eval_rating in incoming_stats.items():
        current_value = current_stats.get(stat)
        evaluator_value = evaluator_stats.get(stat)

        # Sanidad: si falta alguno de los valores necesarios, se ignora
        if current_value is None or evaluator_value is None:
            continue

        evaluator_diff = evaluator_value - current_value
        delta = eval_rating - 50  # cuánto por encima o debajo del neutro

        influence = (abs(evaluator_diff) + 1) / 50

        if delta > 0:
            elo_modifier = 1.0 + (elo_scale * 0.5)
        else:
            elo_modifier = 1.0 - (elo_scale * 0.5)

        raw_change = delta * influence * 0.1 * elo_modifier
        raw_change = max(min(raw_change, 5), -5)

        # Si hay una intención de cambio pero se redondearía a cero, forzamos +/-1
        if 0 < abs(raw_change) < 1:
            raw_change = 1 if raw_change > 0 else -1

        new_value = current_value + raw_change
        updated_stats[stat] = int(round(max(0, min(100, new_value))))


    return updated_stats

