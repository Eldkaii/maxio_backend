from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException


from io import BytesIO
import os
from src.config import settings

import math
from PIL import Image, ImageDraw, ImageFont
# ---------- Helpers ----------

def _load_template(path: str) -> Image.Image:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template no encontrado en {path}")
    return Image.open(path).convert("RGBA")




def _load_fonts(
    template_height: int,
    font_dir: str,
    *,
    name_scale: float = 0.05,
    stats_scale: float = 0.027
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


def _draw_player_photo(template: Image.Image, player, legacy: bool = False) -> None:
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
    foto_height = int(template.height * (0.50 if legacy else 0.46))
    foto = foto.resize((foto_width, foto_height))

    x = (template.width - foto_width) // 2
    y = int(template.height * (0.15 if legacy else 0.14))

    template.paste(foto, (x, y), foto)



def _draw_player_name(
    draw: ImageDraw.ImageDraw,
    template: Image.Image,
    name: str,
    font: ImageFont.FreeTypeFont,
    legacy: bool = False,
) -> None:

    NAME_Y_RATIO = 0.65 if legacy else 0.615
    y = int(template.height * NAME_Y_RATIO)

    bbox = font.getbbox(name)
    text_width = bbox[2] - bbox[0]

    x = (template.width - text_width) // 2

    shadow_offset = (2, 3)
    shadow_color = (0, 0, 0, 90)

    stroke_color = (200, 200, 200) if legacy else (8, 18, 31)
    stroke_width = 2
    text_color = (0, 0, 0) if legacy else (222, 255, 105)

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
    font: ImageFont.FreeTypeFont,
    legacy: bool = False,
) -> None:
    if legacy:
        _draw_legacy_player_stats(draw, template, player, font)
        return

    # The current vertical frame has six dedicated slots across its lower band.
    # Draw each stat at the center of its slot instead of using the prior 3x2 grid.
    overall = round(
        (player.tiro + player.ritmo + player.fisico + player.defensa + player.aura) / 5
    )
    stats = [
        ("TIR", player.tiro), ("DEF", player.defensa), ("RIT", player.ritmo),
        ("AUR", player.aura), ("FIS", player.fisico), ("OVR", overall),
    ]
    centers = [int(template.width * ratio) for ratio in (0.20, 0.32, 0.44, 0.56, 0.68, 0.80)]
    label_y = int(template.height * 0.756)
    value_y = int(template.height * 0.796)
    for (label, value), x in zip(stats, centers):
        draw.text((x, label_y), label, fill=(145, 194, 238), font=font, anchor="mm",
                  stroke_width=1, stroke_fill=(0, 10, 20))
        draw.text((x, value_y), str(int(value)), fill=(242, 248, 255), font=font, anchor="mm",
                  stroke_width=1, stroke_fill=(0, 10, 20))
    return


def _draw_legacy_player_stats(
    draw: ImageDraw.ImageDraw,
    template: Image.Image,
    player,
    font: ImageFont.FreeTypeFont,
) -> None:
    """Renderiza la distribución 3x2 de la carta dorada original."""
    grid_start_x = int(template.width * 0.28)
    column_width = int(template.width * 0.22)
    base_y = int(template.height * 0.74)
    row_spacing = int(font.size * 1.35)
    overall = round((player.tiro + player.ritmo + player.fisico + player.defensa + player.aura) / 5)
    stats = [
        ("TIR", player.tiro), ("DEF", player.defensa), ("RIT", player.ritmo),
        ("AUR", player.aura), ("FIS", player.fisico), ("OVR", overall),
    ]
    gaps = {"TIR": 5, "RIT": 5, "FIS": 5, "DEF": 7, "AUR": 5, "OVR": 7}

    for row_index, row_stats in enumerate((stats[0:2], stats[2:4], stats[4:6])):
        y = base_y + row_index * row_spacing
        for col_index, (label, value) in enumerate(row_stats):
            x_label = grid_start_x + column_width * col_index
            label_width = font.getbbox(label)[2]
            x_value = x_label + label_width + gaps.get(label, 6)
            for dx, dy, color in ((0, -1, (235, 235, 235)), (0, 1, (70, 70, 70))):
                draw.text((x_label + dx, y + dy), label, color, font)
                draw.text((x_value + dx, y + dy), str(int(value)), color, font)
            draw.text((x_label, y), label, (180, 180, 180), font)
            draw.text((x_value, y), str(int(value)), (215, 215, 215), font)







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
        ("MAG", player.aura),
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
