# src/services/player_service.py
import os
from typing import Optional,Dict

from src.models.player import Player, PlayerRelation
from sqlalchemy.orm import Session
from src.models.user import User
from src.schemas.player_schema import PlayerStatsUpdate
from src.utils.logger_config import app_logger as logger
from src.utils.stat_calculator import calculate_updated_stats
from src.config import settings

from fastapi import APIRouter, Depends, HTTPException

from src.database import SessionLocal
from pathlib import Path
import uuid



def create_player_for_user(user: User, db: Session, stats: Optional[Dict[str, int]] = None, is_bot: Optional[bool] = False) -> Player:
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
        magia=stats.get("magia", 50),
        is_bot=is_bot,
    )

    # logger.info(f"Creando player: {player.name} con stats: tiro={player.tiro}, ritmo={player.ritmo}, "
    #             f"fisico={player.fisico}, defensa={player.defensa}, magia={player.magia}")

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
        f.write(image_bytes)

    # 🗄️ Persistir en DB
    player.photo_path = photo_path
    db.add(player)
    db.commit()
    db.refresh(player)

    print("📸 Foto guardada en:", photo_path)

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
        "magia": target.magia,
    }

    evaluator_stats = {
        "tiro": evaluator.tiro,
        "ritmo": evaluator.ritmo,
        "fisico": evaluator.fisico,
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
    location_fonts = settings.DEFAULT_FONTS_PATH
    fonts = _load_fonts(template.height,location_fonts)

    _draw_player_photo(template, player)
    _draw_player_name(draw, template, player.name, fonts["name"])
    _draw_player_stats(draw, template, player, fonts["stats"])
    _draw_player_stats_star(draw, template, player,fonts["stats"])

    return _save_to_buffer(template)


# ---------- Helpers ----------

def _load_template(path: str) -> Image.Image:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template no encontrado en {path}")
    return Image.open(path).convert("RGBA")




def _load_fonts(
    template_height: int,
    font_dir: str,
    *,
    name_scale: float = 0.08,
    stats_scale: float = 0.05 #0.022
) -> dict:
    """
    Carga las fuentes necesarias para la carta a partir de un directorio.

    El directorio debe contener:
        - name.(ttf|otf)   -> fuente para el nombre
        - stats.(ttf|otf)  -> fuente para stats

    Args:
        template_height: altura del template en píxeles
        font_dir: ruta al directorio de fuentes
        name_scale: proporción de la altura para el nombre
        stats_scale: proporción de la altura para stats

    Returns:
        dict con las fuentes cargadas
    """

    font_dir = Path(font_dir)

    name_size = int(template_height * name_scale)
    stats_size = int(template_height * stats_scale)

    def _find_font(filename_base: str) -> Path:
        for ext in ("ttf", "otf"):
            path = font_dir / f"{filename_base}.{ext}"
            if path.exists():
                return path
        raise FileNotFoundError(
            f"No se encontró {filename_base}.ttf ni {filename_base}.otf en {font_dir}"
        )

    try:
        name_font_path = _find_font("Retro_Boulevard")
        stats_font_path = _find_font("Retro_Boulevard")

        return {
            "name": ImageFont.truetype(str(name_font_path), name_size),
            "stats": ImageFont.truetype(str(stats_font_path), stats_size),
        }

    except Exception as e:
        raise RuntimeError(f"Error cargando fuentes desde {font_dir}: {e}")


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

    NAME_Y_RATIO = 0.65
    y = int(template.height * NAME_Y_RATIO)

    bbox = font.getbbox(name)
    text_width = bbox[2] - bbox[0]

    x = (template.width - text_width) // 2

    shadow_offset = (2, 3)
    shadow_color = (0, 0, 0, 90)

    stroke_color = (200, 200, 200)
    stroke_width = 2
    text_color = (0, 0, 0)

    # Sombra
    draw.text(
        (x + shadow_offset[0], y + shadow_offset[1]),
        name,
        fill=shadow_color,
        font=font
    )

    # Stroke
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

    # Texto principal
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

    # =====================
    # Layout base
    # =====================
    CARD_MARGIN_RATIO = 0.08
    LEFT_PADDING_RATIO = 0.03
    STATS_Y_RATIO = 0.75
    COLUMNS = 3

    card_margin_x = int(template.width * CARD_MARGIN_RATIO)
    left_padding = int(template.width * LEFT_PADDING_RATIO)

    grid_start_x = card_margin_x + left_padding
    available_width = template.width - (grid_start_x * 2)
    column_width = available_width // COLUMNS

    row_spacing = int(font.size * 1.3)
    base_y = int(template.height * STATS_Y_RATIO)

    # =====================
    # Stats
    # =====================
    overall = round(
        (player.tiro +
         player.ritmo +
         player.fisico +
         player.defensa +
         player.magia) / 5
    )

    stats = [
        ("TIR", player.tiro),
        ("RIT", player.ritmo),
        ("MAG", player.magia),
        ("DEF", player.defensa),
        ("FIS", player.fisico),
        ("OVR", overall),
    ]

    rows = [stats[:3], stats[3:]]

    # =====================
    # Separación label → valor (CONFIGURABLE)
    # =====================
    VALUE_GAPS = {
        "TIR": 7,
        "RIT": 5,
        "FIS": 5,
        "DEF": 5,
        "MAG": 5,
        "OVR": 5,
    }
    # ⬆️ vos después ajustás estos valores a gusto

    # =====================
    # Colores & relieve
    # =====================
    label_color = (180, 180, 180)
    value_color = (215, 215, 215)

    highlight_color = (235, 235, 235)
    shadow_color = (70, 70, 70)

    offset = 1
    highlight_offsets = [(0, -offset)]
    shadow_offsets = [(0, offset)]

    # =====================
    # Render
    # =====================
    for row_index, row_stats in enumerate(rows):
        y = base_y + row_index * row_spacing

        for i, (label, value) in enumerate(row_stats):
            label_text = label
            value_text = str(int(value))

            x_col = grid_start_x + column_width * i

            label_width = font.getbbox(label_text)[2]
            gap = VALUE_GAPS.get(label, 6)

            x_label = x_col
            x_value = x_label + label_width + gap

            # Label
            for dx, dy in highlight_offsets:
                draw.text((x_label + dx, y + dy), label_text, highlight_color, font)
            for dx, dy in shadow_offsets:
                draw.text((x_label + dx, y + dy), label_text, shadow_color, font)
            draw.text((x_label, y), label_text, label_color, font)

            # Value
            for dx, dy in highlight_offsets:
                draw.text((x_value + dx, y + dy), value_text, highlight_color, font)
            for dx, dy in shadow_offsets:
                draw.text((x_value + dx, y + dy), value_text, shadow_color, font)
            draw.text((x_value, y), value_text, value_color, font)





import math
from PIL import Image, ImageDraw, ImageFont

def _draw_player_stats_star(
    draw: ImageDraw.ImageDraw,
    template: Image.Image,
    player,
    font: ImageFont.FreeTypeFont = None,
    font_scale: float = 0.4,
    offset_x_ratio: float = 0.19,
    offset_y_ratio: float = 0.2,
    scale: float = 0.8,
):
    #OFSETS
    # x = 0.0 → borde izquierdo
    #
    # x = 1.0 → borde derecho
    #
    # y = 0.0 → borde superior
    #
    # y = 1.0 → borde inferior

    def _stat_color(value: float) -> tuple[int, int, int, int]:
        """
        value: normalized (0..1)
        """
        if value < 0.40:
            return (220, 50, 50, 140)      # rojo
        elif value < 0.80:
            return (230, 200, 40, 140)    # amarillo
        else:
            return (60, 200, 80, 140)     # verde

    stats = [
        ("MAG", player.magia),
        ("PUN", player.tiro),
        ("VEL", player.ritmo),
        ("RES", player.fisico),
        ("DEF", player.defensa),
    ]

    max_value = 100
    normalized = [min(max(v, 0), max_value) / max_value for _, v in stats]

    outline_color = (80, 80, 80, 200)
    grid_color = (0, 0, 0, 120)

    # 📐 Layout
    base_size = template.width * 0.26
    size = int(base_size * scale)

    cx = int(template.width * offset_x_ratio)
    cy = int(template.height * offset_y_ratio)

    # 🅰 Fuente
    if font is None:
        font_size = max(6, int(template.height * 0.012 * font_scale))
        font = ImageFont.truetype(
            str(settings.DEFAULT_FONTS_PATH / "Retro_Boulevard.ttf"),
            font_size,
        )

    # ==========================================================
    # 🧱 Capa del RADAR (grid)
    # ==========================================================
    radar_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rdraw = ImageDraw.Draw(radar_layer)

    center = (size // 2, size // 2)
    radius = size * 0.45

    for f in [0.2, 0.4, 0.6, 0.8, 1.0]:
        pts = []
        for i in range(5):
            a = math.radians(90 + i * 72)
            pts.append((
                center[0] + math.cos(a) * radius * f,
                center[1] - math.sin(a) * radius * f,
            ))
        rdraw.polygon(pts, outline=grid_color)

    # ==========================================================
    # ⭐ Capa ESTRELLA (relleno por stats)
    # ==========================================================
    star_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(star_layer)

    star_pts = []
    for i, v in enumerate(normalized):
        a = math.radians(90 + i * 72)
        star_pts.append((
            center[0] + math.cos(a) * radius * v,
            center[1] - math.sin(a) * radius * v,
        ))

    # 🔴🟡🟢 Relleno por triángulos
    for i in range(5):
        tri_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        tdraw = ImageDraw.Draw(tri_layer)

        p1 = star_pts[i]
        p2 = star_pts[(i + 1) % 5]

        v1 = normalized[i]
        v2 = normalized[(i + 1) % 5]

        sector_value = max(v1, v2)
        color = _stat_color(sector_value)

        tdraw.polygon(
            [center, p1, p2],
            fill=color
        )

        # composición correcta (NO paste)
        star_layer = Image.alpha_composite(star_layer, tri_layer)

    # contorno estrella
    sdraw.line(
        star_pts + [star_pts[0]],
        fill=outline_color,
        width=2
    )

    # ==========================================================
    # 🧬 COMPOSICIÓN REAL (clave)
    # ==========================================================
    combined = Image.alpha_composite(radar_layer, star_layer)

    # pegar sobre la tarjeta
    template.alpha_composite(
        combined,
        (cx - size // 2, cy - size // 2)
    )

    # ==========================================================
    # 🏷 Etiquetas
    # ==========================================================
    label_r = radius + 14
    for i, (label, value) in enumerate(stats):
        a = math.radians(90 + i * 72)
        x = cx + math.cos(a) * label_r
        y = cy - math.sin(a) * label_r

        text = f"{label} {int(value)}"
        bbox = font.getbbox(text)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        deg = max(-45, min(45, math.degrees(a) - 90))

        tmp = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        td.text((2, 2), text, fill=(0, 0, 0, 220), font=font)

        rot = tmp.rotate(-deg, expand=True)
        # template.alpha_composite(
        #     rot,
        #     (int(x - rot.width / 2), int(y - rot.height / 2))
        # )




def _save_to_buffer(image: Image.Image) -> BytesIO:
    buffer = BytesIO()
    buffer.name = "carta.png"
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
