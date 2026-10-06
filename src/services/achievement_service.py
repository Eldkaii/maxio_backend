"""Reglas centralizadas para los logros visibles en el perfil de jugador."""

from fastapi import HTTPException

from src.models.player import Player


CLUB_AFFINITIES = {"bolso", "manya", "none"}


def build_player_achievements(player: Player) -> dict:
    """Devuelve los logros obtenidos y el estado de la elección de afinidad."""
    badges: list[dict] = []
    nationality = (player.user.nationality if player.user else "").upper()

    if not player.is_bot and nationality == "UY":
        badges.append({
            "key": "charrua",
            "name": "CHARRÚA",
            "symbol": "✦",
            "description": "Jugador con nacionalidad uruguaya.",
        })

    affinity = player.club_affinity
    if affinity == "bolso":
        badges.append({
            "key": "bolso",
            "name": "BOLSO",
            "symbol": "◆",
            "description": "Afinidad elegida tras completar diez partidos.",
        })
    elif affinity == "manya":
        badges.append({
            "key": "manya",
            "name": "MANYA",
            "symbol": "▲",
            "description": "Afinidad elegida tras completar diez partidos.",
        })

    return {
        "badges": badges,
        "club_choice_available": (
            not player.is_bot
            and (player.cant_partidos or 0) >= 10
            and affinity is None
        ),
        "club_affinity": affinity,
    }


def choose_player_club_affinity(player: Player, affinity: str) -> dict:
    """Registra una única decisión de afinidad cuando el logro está habilitado."""
    normalized_affinity = (affinity or "").strip().lower()
    if normalized_affinity not in CLUB_AFFINITIES:
        raise HTTPException(status_code=422, detail="Afinidad de club inválida.")
    if player.is_bot:
        raise HTTPException(status_code=400, detail="Los bots no pueden elegir afinidad de club.")
    if (player.cant_partidos or 0) < 10:
        raise HTTPException(status_code=400, detail="La elección se habilita al completar 10 partidos.")
    if player.club_affinity is not None:
        raise HTTPException(status_code=409, detail="La afinidad de club ya fue elegida.")

    player.club_affinity = normalized_affinity
    return build_player_achievements(player)
