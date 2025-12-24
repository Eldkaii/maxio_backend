# src/services/player_service.py
import os
from typing import Optional,Dict

from sqlalchemy.testing import db

from src.models.player import Player, PlayerRelation
from sqlalchemy.orm import Session
from src.models.user import User
from src.schemas.player_schema import PlayerStatsUpdate
from src.utils.logger_config import app_logger as logger
from src.utils.stat_calculator import calculate_updated_stats
from src.config import settings

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from src.database import SessionLocal
import uuid



def create_player_for_user(user: User, db: Session, stats: Optional[Dict[str, int]] = None, is_bot: Optional[bool] = False) -> Player:
    stats = stats or {}

    player = Player(
        name=user.username,
        cant_partidos=0,
        elo=1000,
        user_id=user.id,
        punteria=stats.get("punteria", 50),
        velocidad=stats.get("velocidad", 50),
        resistencia=stats.get("resistencia", 50),
        defensa=stats.get("defensa", 50),
        magia=stats.get("magia", 50),
        is_bot=is_bot,
    )

    # logger.info(f"Creando player: {player.name} con stats: punteria={player.punteria}, velocidad={player.velocidad}, "
    #             f"resistencia={player.resistencia}, defensa={player.defensa}, magia={player.magia}")

    db.add(player)
    db.commit()
    db.refresh(player)

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

    Args:
        username: username del jugador
        image_bytes: bytes de la imagen
        filename: nombre original del archivo (para obtener extensión)
        db: sesión activa de SQLAlchemy

    Returns:
        photo_path guardado
    """

    player: Player = get_player_by_username(username, db)

    # 📁 Carpeta base desde config
    base_folder = settings.API_PHOTO_PLAYER_PATH_FOLDER
    os.makedirs(base_folder, exist_ok=True)

    # 🧩 Extensión segura
    _, ext = os.path.splitext(filename)
    ext = ext.lower() if ext else ".png"

    # 🆔 Nombre único
    photo_filename = f"{username}_{uuid.uuid4().hex}{ext}"
    photo_path = os.path.join(base_folder, photo_filename)

    # 💾 Guardar archivo
    with open(photo_path, "wb") as f:
        f.write(image_bytes)

    # 🗄️ Persistir en DB
    player.photo_path = photo_path
    db.add(player)
    db.commit()
    db.refresh(player)

    return photo_path

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
        "punteria": target.punteria,
        "velocidad": target.velocidad,
        "resistencia": target.resistencia,
        "defensa": target.defensa,
        "magia": target.magia,
    }

    evaluator_stats = {
        "punteria": evaluator.punteria,
        "velocidad": evaluator.velocidad,
        "resistencia": evaluator.resistencia,
        "defensa": evaluator.defensa,
        "magia": evaluator.magia,
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


def generate_player_card_from_player(player):
    """
    Genera la carta de un jugador usando un template.
    Foto arriba, nombre centrado, stats alineados abajo.
    """

    template = _load_template(settings.API_CARD_TEMPLATE_PATH)
    draw = ImageDraw.Draw(template)

    fonts = _load_fonts(template.height)

    _draw_player_photo(template, player)
    _draw_player_name(draw, template, player.name, fonts["large"])
    _draw_player_stats(draw, template, player, fonts["small"])

    return _save_to_buffer(template)


# ---------- Helpers ----------

def _load_template(path: str) -> Image.Image:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template no encontrado en {path}")
    return Image.open(path).convert("RGBA")


def _load_fonts(template_height: int) -> dict:
    NAME_SCALE = 0.04 * 2
    STATS_SCALE = 0.025 * 1.5

    large_size = int(template_height * NAME_SCALE)
    small_size = int(template_height * STATS_SCALE)

    try:
        font_large = ImageFont.truetype("DejaVuSans-Bold.ttf", large_size)
        font_small = ImageFont.truetype("DejaVuSans-Bold.ttf", small_size)
    except Exception as e:
        raise RuntimeError(f"Error cargando fuentes: {e}")

    return {
        "large": font_large,
        "small": font_small
    }


def _draw_player_photo(template: Image.Image, player) -> None:
    # imagen por defecto
    DEFAULT_PHOTO_PATH = settings.DEFAULT_PHOTO_PATH

    photo_path = None

    # decidir qué imagen usar
    if getattr(player, "photo_path", None) and os.path.exists(player.photo_path):
        photo_path = player.photo_path
    elif os.path.exists(DEFAULT_PHOTO_PATH):
        photo_path = DEFAULT_PHOTO_PATH
    else:
        # si ni siquiera existe la imagen por defecto, no dibujamos nada
        return

    foto = Image.open(photo_path).convert("RGBA")

    foto_width = int(template.width * 0.7)
    foto_height = int(template.height * 0.5)
    foto = foto.resize((foto_width, foto_height))

    x = (template.width - foto_width) // 2
    y = int(template.height * 0.15)

    template.paste(foto, (x, y), foto)


def _draw_player_name(
    draw: ImageDraw.ImageDraw,
    template: Image.Image,
    name: str,
    font: ImageFont.FreeTypeFont
) -> None:

    NAME_Y_RATIO = 0.68
    y = int(template.height * NAME_Y_RATIO)

    text_width = font.getbbox(name)[2]
    x = (template.width - text_width) // 2

    # ---- Configuración visual ----
    shadow_offset = (2, 3)
    shadow_color = (0, 0, 0, 90)

    stroke_color = (200, 200, 200)  # plateado
    stroke_width = 2                # grosor del borde

    text_color = (0, 0, 0)

    # ---- Sombra ----
    draw.text(
        (x + shadow_offset[0], y + shadow_offset[1]),
        name,
        fill=shadow_color,
        font=font
    )

    # ---- Borde (stroke plateado) ----
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text(
                (x + dx, y + dy),
                name,
                fill=stroke_color,
                font=font
            )

    # ---- Texto principal ----
    draw.text(
        (x, y),
        name,
        fill=text_color,
        font=font
    )



def _draw_player_stats(
    draw: ImageDraw.ImageDraw,
    template: Image.Image,
    player,
    font: ImageFont.FreeTypeFont
) -> None:
    stats = [
        ("PUN", player.punteria),
        ("VEL", player.velocidad),
        ("RES", player.resistencia),
        ("DEF", player.defensa),
        ("MAG", player.magia),
    ]

    rows = [
        stats[:3],
        stats[3:],
    ]

    STATS_Y_RATIO = 0.94
    base_y = int(template.height * 0.83) * STATS_Y_RATIO
    row_spacing = int(font.size * 1.3)
    margin_x = int(template.width * 0.08)

    # ---- Estilo "piedra tallada" ----
    # ---- Colores piedra ----
    main_color = (180, 180, 180)  # gris piedra
    shadow_color = (70, 70, 70)  # sombra profunda
    highlight_color = (215, 215, 215)  # relieve claro

    # Offsets más agresivos (clave)
    shadow_offsets = [(3, 3), (2, 2)]
    highlight_offsets = [(-3, -3), (-2, -2)]

    for row_index, row_stats in enumerate(rows):
        y = base_y + row_index * row_spacing
        available_width = template.width - (margin_x * 2)
        spacing = available_width // len(row_stats)

        for i, (label, value) in enumerate(row_stats):
            text = f"{label} {int(value)}"
            text_width = font.getbbox(text)[2]

            x = margin_x + spacing * i + (spacing - text_width) // 2

            # ---- Relieve claro (arriba-izquierda) ----
            for dx, dy in highlight_offsets:
                draw.text(
                    (x + dx, y + dy),
                    text,
                    fill=highlight_color,
                    font=font
                )

            # ---- Sombra oscura (abajo-derecha) ----
            for dx, dy in shadow_offsets:
                draw.text(
                    (x + dx, y + dy),
                    text,
                    fill=shadow_color,
                    font=font
                )

            # ---- Cara del texto (principal) ----
            draw.text(
                (x - 1, y - 1),
                text,
                fill=main_color,
                font=font
            )

            # ---- Texto principal ----
            draw.text(
                (x, y),
                text,
                fill=main_color,
                font=font
            )


def _save_to_buffer(image: Image.Image) -> BytesIO:
    buffer = BytesIO()
    buffer.name = "carta.png"
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
