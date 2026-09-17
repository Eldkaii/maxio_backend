# src/services/player_service.py

from typing import Optional,Dict

from src.models import TeamEnum
from src.models.player import Player, PlayerRelation
from src.models.player_evaluation import PlayerEvaluationPermission
from sqlalchemy.orm import Session
from src.models.user import User
from src.schemas.player_schema import PlayerStatsUpdate
from src.services.player_service_image import _load_template, _draw_player_photo, _draw_player_name, _draw_player_stats, \
    _draw_player_stats_star, _save_to_buffer, _load_fonts
from src.utils.logger_config import app_logger as logger
from src.utils.stat_calculator import calculate_updated_stats
from src.config import settings

from fastapi import APIRouter, Depends, HTTPException


from src.database import SessionLocal

import uuid


def _normalize_player_photo(image_bytes: bytes) -> tuple[bytes, str]:
    """Normalize every avatar to the exact dimensions of no_face.png."""
    from io import BytesIO
    from PIL import Image, ImageOps
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            source = ImageOps.exif_transpose(source).convert("RGBA")
            with Image.open(settings.DEFAULT_PHOTO_PATH) as default:
                target_width, target_height = default.size
            target_ratio = target_width / target_height
            source_ratio = source.width / source.height
            if source_ratio > target_ratio:
                crop_width = max(1, round(source.height * target_ratio))
                left = (source.width - crop_width) // 2
                source = source.crop((left, 0, left + crop_width, source.height))
            elif source_ratio < target_ratio:
                crop_height = max(1, round(source.width / target_ratio))
                top = (source.height - crop_height) // 2
                source = source.crop((0, top, source.width, top + crop_height))
            normalized = source.resize((target_width, target_height), Image.Resampling.LANCZOS)
            output = BytesIO()
            normalized.save(output, format="PNG", optimize=True)
            return output.getvalue(), ".png"
    except (OSError, ValueError, ZeroDivisionError) as exc:
        raise ValueError("No se pudo procesar la imagen") from exc



def create_player_for_user(
    user: User,
    db: Session,
    stats: Optional[Dict[str, int]] = None,
    is_bot: Optional[bool] = False
) -> Player:

    stats = stats or {}

    player = Player(
        name=user.username,
        cant_partidos=0,
        elo=1000,
        user_id=user.id,
        tiro=stats.get("tiro", 50),
        ritmo=stats.get("ritmo", 50),
        fisico=stats.get("fisico", 50),
        defensa=stats.get("defensa", 50),
        aura=stats.get("aura", 50),
        is_bot=is_bot,
    )

    db.add(player)
    return player

def get_player_by_username(username: str, db: Session) -> Player:
    player = db.query(Player).filter(Player.name == username).first()
    if not player:
        raise ValueError(f"Player con username '{username}' no encontrado")
    logger.info(f"Player obtenido: {username}")
    return player

def save_player_photo(
    username: str,
    image_bytes: bytes,
    filename: str,
    db: Session
) -> str:
    """
    Guarda la foto de un jugador y actualiza su photo_path.

    Returns:
        Nombre del archivo guardado
    """

    player: Player = get_player_by_username(username, db)
    if not player:
        raise HTTPException(
            status_code=404,
            detail="Jugador no encontrado"
        )

    # 📁 Carpeta base
    base_folder = settings.API_PHOTO_PLAYER_PATH_FOLDER.resolve()
    os.makedirs(base_folder, exist_ok=True)

    # 🧩 Extensión segura
    _, ext = os.path.splitext(filename or "")
    ext = ext.lower() if ext in {".png", ".jpg", ".jpeg", ".webp"} else ".png"

    # Normalizar galeria, camara y mensajeria al mismo lienzo canonico.
    normalized_bytes, ext = _normalize_player_photo(image_bytes)

    # 🆔 Nombre único
    photo_filename = f"{username}_{uuid.uuid4().hex}{ext}"
    photo_path = os.path.join(base_folder, photo_filename)

    # 🗑️ Eliminar foto anterior si existe
    if player.photo_path:
        old_path = os.path.join(base_folder, player.photo_path)
        if os.path.exists(old_path):
            os.remove(old_path)

    # 💾 Guardar archivo
    with open(photo_path, "wb") as f:
        f.write(normalized_bytes)

    # 🗄️ Persistir en DB
    player.photo_path = photo_path
    db.add(player)
    db.commit()
    db.refresh(player)

    print("Foto guardada en:", photo_path)

    return photo_filename

def add_player_relation(player1_id: int, player2_id: int, together: bool, db: Session):
    logger.info(f"Agregando {player1_id} - {player2_id}  un nuevo juego {together} juntos")
    if player1_id == player2_id:
        raise ValueError("Un jugador no puede relacionarse consigo mismo.")

    # Asegurar orden consistente para evitar duplicados (simetría)
    p1, p2 = sorted((player1_id, player2_id))

    relation = db.query(PlayerRelation).filter_by(player1_id=p1, player2_id=p2).first()
    if relation:
        if together:
            relation.games_together += 1
        else:
            relation.games_apart += 1
    else:
        if together:
            relation = PlayerRelation(
                player1_id=p1,
                player2_id=p2,
                games_together=1
            )
        else:
            relation = PlayerRelation(
                player1_id=p1,
                player2_id=p2,
                games_apart=1
            )
        db.add(relation)

    db.commit()
    db.refresh(relation)
    return relation

def update_player_stats(
    target_username: str,
    evaluator_username: str,
    stats_data: PlayerStatsUpdate,
    db: Session
) -> Player:
    # Buscar al jugador que fue evaluado
    target = db.query(Player).filter(Player.name == target_username).first()
    if not target:
        raise ValueError(f"Jugador evaluado '{target_username}' no encontrado")

    # Buscar al jugador que hizo la evaluación
    evaluator = db.query(Player).filter(Player.name == evaluator_username).first()
    if not evaluator:
        raise ValueError(f"Jugador evaluador '{evaluator_username}' no encontrado")

    current_stats = {
        "tiro": target.tiro,
        "ritmo": target.ritmo,
        "fisico": target.fisico,
        "defensa": target.defensa,
        "aura": target.aura,
    }

    evaluator_stats = {
        "tiro": evaluator.tiro,
        "ritmo": evaluator.ritmo,
        "fisico": evaluator.fisico,
        "defensa": evaluator.defensa,
        "aura": evaluator.aura,
    }

    elo = target.elo

    # Solo los stats efectivamente enviados
    incoming_stats = stats_data.dict(exclude_unset=True)

    # Calcular nuevos stats ponderados
    new_stats = calculate_updated_stats(
        current_stats=current_stats,
        evaluator_stats=evaluator_stats,
        incoming_stats=incoming_stats,
        elo=elo
    )

    for key, value in new_stats.items():
        setattr(target, key, value)

    db.commit()
    db.refresh(target)
    # Cada permiso de evaluación es de un solo uso. Al completar la
    # evaluación se consume para impedir que el mismo jugador sea evaluado
    # repetidamente por el mismo evaluador.
    permission = db.query(PlayerEvaluationPermission).filter_by(
        evaluator_id=evaluator.id,
        target_id=target.id,
    ).first()
    if permission:
        db.delete(permission)
        db.commit()
    #logger.info(f"Stats actualizados para player {target_username} (puntuado por {evaluator_username}), nuevo stat [{new_stats}]")
    return target

def calculate_elo(cant_partidos: int, cant_partidos_ganados: int, recent_results: list[bool], current_elo: int) -> int:
    # Si no ha jugado partidos, asignamos un ELO inicial
    if cant_partidos == 0:
        return 1000

    # Si tiene menos de 10 partidos, usamos un sistema más suave
    if cant_partidos < 10:
        # Valor base neutral
        base_elo = 1000
        win_rate = cant_partidos_ganados / cant_partidos
        adjustment = int((win_rate - 0.5) * 100)  # más suave que el normal
        return max(0, min(2000, base_elo + adjustment))

    # A partir de 10 partidos, se aplica la lógica completa
    win_rate = cant_partidos_ganados / cant_partidos

    streak_bonus = 0
    streak_penalty = 0

    if recent_results:
        streak_score = sum(1 if r else -1 for r in recent_results)

        if streak_score > 0:
            streak_bonus = streak_score * 5
        elif streak_score < 0:
            streak_penalty = abs(streak_score) * 7

    base_change = int((win_rate - 0.5) * 200)
    new_elo = current_elo + base_change + streak_bonus - streak_penalty

    return max(0, min(2000, new_elo))

def update_player_match_history(username: str, won: bool, db: Session):
    player = db.query(Player).filter_by(name=username).first()
    if not player:
        raise ValueError(f"Player with username '{username}' not found")

    # Actualizar historial de partidos
    player.cant_partidos += 1
    if won:
        player.cant_partidos_ganados += 1

    # Actualizar resultados recientes (máximo 10)
    if player.recent_results is None:
        player.recent_results = []
    player.recent_results = (player.recent_results or []) + [won]
    player.recent_results = player.recent_results[-10:]

    # Recalcular ELO
    player.elo = calculate_elo(
        cant_partidos=player.cant_partidos,
        cant_partidos_ganados=player.cant_partidos_ganados,
        recent_results=player.recent_results,
        current_elo=player.elo,
    )

    db.commit()

def get_or_create_relation(
    player1_id: int,
    player2_id: int,
    db: Session,
    new_game_together: Optional[bool] = None
) -> PlayerRelation:
    # Ordenar para evitar duplicados cruzados
    p1, p2 = sorted([player1_id, player2_id])
    relation = db.query(PlayerRelation).filter_by(player1_id=p1, player2_id=p2).first()

    if not relation:
        relation = PlayerRelation(player1_id=p1, player2_id=p2, games_together=0, games_apart=0)
        db.add(relation)

    # Si se indica actualización, actualizar contador y guardar
    if new_game_together is not None:
        if new_game_together:
            relation.games_together += 1
        else:
            relation.games_apart += 1


        db.commit()
        db.refresh(relation)

    return relation


def build_full_player_profile(
    db: Session,
    username: str,
    recent_matches_limit: int = 5
) -> dict:
    player = db.query(Player).filter(Player.name == username).first()
    if not player:
        raise ValueError(f"Player '{username}' not found")

    # --------------------
    # Stats
    # --------------------
    stats = {
        "tiro": round(player.tiro, 1),
        "ritmo": round(player.ritmo, 1),
        "fisico": round(player.fisico, 1),
        "defensa": round(player.defensa, 1),
        "aura": round(player.aura, 1),
        "elo": player.elo,
    }

    played = player.cant_partidos or 0
    won = player.cant_partidos_ganados or 0
    winrate = round((won / played) * 100, 1) if played else 0.0

    matches_summary = {
        "played": played,
        "won": won,
        "winrate": winrate,
        "recent_results": player.recent_results[-10:] if player.recent_results else [],
    }

    # --------------------
    # Relaciones
    # --------------------
    relations = {
        "top_allies": [
            {"id": p.id, "name": p.name, "games_together": games}
            for p, games in player.top_allies(db, limit=3, exclude_bots=True)
        ],
        "top_opponents": [
            {"id": p.id, "name": p.name, "games_apart": games}
            for p, games in player.top_opponents(db, limit=3, exclude_bots=True)
        ],
        "most_played_with": [
            {"id": p.id, "name": p.name, "total_games": games}
            for p, games in player.top_teammates(db, limit=5, exclude_bots=True)
        ],
    }

    # --------------------
    # Evaluation permissions
    # --------------------
    evaluation = {
        "can_evaluate": [
            {"id": perm.target.id, "name": perm.target.name}
            for perm in player.evaluation_permissions_given
        ]
    }

    # --------------------
    # Últimos partidos
    # --------------------
    recent_matches = []
    associations = sorted(
        player.match_associations,
        key=lambda ma: ma.match.date,
        reverse=True
    )[:recent_matches_limit]

    for assoc in associations:
        match = assoc.match
        my_team = assoc.team

        # Las respuestas se comparten entre la notificación y la mini-app:
        # una única fila por usuario/partido representa la respuesta enviada.
        from src.models import MatchResultReply
        replies = {
            reply.user_id: reply.result
            for reply in db.query(MatchResultReply).filter(
                MatchResultReply.match_id == match.id
            ).all()
        }

        teammates = [{
            "id": player.id,
            "name": player.name,
            "response": "bot" if player.is_bot else replies.get(player.user_id, "pending"),
        }]
        opponents = []

        for mp in match.match_associations:
            if mp.player_id == player.id:
                continue
            entry = {
                "id": mp.player.id,
                "name": mp.player.name,
                "response": "bot" if mp.player.is_bot else replies.get(mp.player.user_id, "pending"),
            }
            if mp.team == my_team:
                teammates.append(entry)
            else:
                opponents.append(entry)

        # Determinar resultado del partido
        if match.winner_team_id is None or my_team is None:
            result = "pending"  # Partido aún no tiene resultado
        elif (
            (my_team == TeamEnum.team1 and match.winner_team_id == match.team1_id) or
            (my_team == TeamEnum.team2 and match.winner_team_id == match.team2_id)
        ):
            result = "win"
        else:
            result = "loss"

        recent_matches.append({
            "match_id": match.id,
            "date": match.date.isoformat(),  # Convertimos a string
            "team": my_team.value if my_team else None,
            "result": result,
            "my_response": "bot" if player.is_bot else replies.get(player.user_id, "pending"),
            "teammates": teammates,
            "opponents": opponents,
        })

    # --------------------
    # Perfil final
    # --------------------
    return {
        "id": player.id,
        "name": player.name,
        "first_name": player.user.first_name if player.user else "",
        "last_name": player.user.last_name if player.user else "",
        "nationality": player.user.nationality if player.user else "UY",
        "is_bot": player.is_bot,
        "cant_partidos": player.cant_partidos,
        "photo_path": player.photo_path,
        "stats": stats,
        "matches_summary": matches_summary,
        "relations": relations,
        "recent_matches": recent_matches,
        "evaluation": evaluation,
    }


def generate_player_card_for_telegram_bot(username: str):
    db = SessionLocal()
    try:
        return generate_player_card(username, db)
    finally:
        db.close()


def generate_player_card(target_username: str, db: Session):
    """
    Genera la carta del jugador como imagen.

    Args:
        target_username: username del Player
    Returns:
        BytesIO con la imagen lista para enviar
        :param db:
    """
    player = get_player_by_username(target_username,db)
    return generate_player_card_from_player(player)


from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os
import random


def generate_player_card_from_player(player):
    """
    Genera la carta de un jugador usando un template.
    Foto arriba, nombre centrado, stats alineados abajo.
    """

    template_path = random.choice(settings.API_CARD_TEMPLATE_PATHS)
    legacy = template_path == settings.API_CARD_TEMPLATE_PATH
    template = _load_template(template_path)
    draw = ImageDraw.Draw(template)
    location_fonts = settings.DEFAULT_FONTS_PATH
    fonts = _load_fonts(
        template.height,
        location_fonts,
        name_scale=0.08 if legacy else 0.05,
        stats_scale=0.05 if legacy else 0.027,
    )

    _draw_player_photo(template, player, legacy=legacy)
    _draw_player_name(draw, template, player.name, fonts["name"], legacy=legacy)
    _draw_player_stats(draw, template, player, fonts["stats"], legacy=legacy)

    return _save_to_buffer(template)


