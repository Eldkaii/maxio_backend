"""Avatar identity, earned equipment and face processing; no external image service."""

from io import BytesIO
from urllib.parse import quote
from uuid import uuid4
import warnings

from fastapi import HTTPException
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
from pydantic import ValidationError

from src.schemas.avatar_schema import AvatarConfig

MAX_FACE_BYTES = 5 * 1024 * 1024
MAX_FACE_PIXELS = 16_000_000

# slot, identifier, label, statistic, threshold, optional club affinity
CATALOG = (
    ("jersey", "training", "Entrenamiento", "matches", 0, None),
    ("jersey", "bolso", "Remera Bolso", "matches", 10, "bolso"),
    ("jersey", "manya", "Remera Manya", "matches", 10, "manya"),
    ("shorts", "basic", "Short de cancha", "matches", 0, None),
    ("shorts", "winner", "Short de campeón", "wins", 5, None),
    ("boots", "classic", "Botines clásicos", "matches", 0, None),
    ("boots", "lime", "Botines Lima", "wins", 10, None),
    ("cap", "none", "Sin gorra", "matches", 0, None),
    ("cap", "street", "Gorra del barrio", "matches", 5, None),
    ("tattoo", "none", "Sin tatuajes", "matches", 0, None),
    ("tattoo", "lightning", "Rayo · antebrazo", "matches", 20, None),
    ("tattoo", "bands", "Bandas · pierna", "matches", 40, None),
)


def wardrobe_catalog(player) -> list[dict]:
    counts = {
        "matches": max(0, player.cant_partidos or 0),
        "wins": max(0, player.cant_partidos_ganados or 0),
    }
    result = []
    for slot, key, name, metric, target, affinity in CATALOG:
        progress = min(counts[metric], target)
        unlocked = not target or (
            not player.is_bot and progress >= target
            and (not affinity or player.club_affinity == affinity)
        )
        requirement = "Disponible desde el inicio"
        if target:
            requirement = f"{target} {'partidos' if metric == 'matches' else 'victorias'}"
            if affinity:
                requirement += f" y afinidad {'Bolso' if affinity == 'bolso' else 'Manya'}"
        result.append(dict(slot=slot, id=key, name=name, requirement=requirement,
                           unlocked=bool(unlocked), progress=progress, target=target))
    return result


def avatar_visual(player) -> dict:
    try:
        config = AvatarConfig.model_validate(player.avatar_config or {})
    except ValidationError:
        config = AvatarConfig()
    # Old/invalid equipment never bypasses the current server-owned catalogue.
    allowed = {(item["slot"], item["id"]) for item in wardrobe_catalog(player) if item["unlocked"]}
    defaults = AvatarConfig().equipment
    for slot, value in config.equipment.model_dump().items():
        if (slot, value) not in allowed:
            setattr(config.equipment, slot, getattr(defaults, slot))
    return {
        "config": config.model_dump(),
        "face_url": (
            f"/player/{quote(player.name, safe='')}/avatar/face?v={player.avatar_face_version}"
            if player.avatar_face_version else None
        ),
    }


def wardrobe_state(player) -> dict:
    return {**avatar_visual(player), "catalog": wardrobe_catalog(player)}


def save_avatar_config(player, config: AvatarConfig) -> dict:
    if player.is_bot:
        raise HTTPException(403, "Los bots no pueden editar este vestuario.")
    catalog = {(item["slot"], item["id"]): item for item in wardrobe_catalog(player)}
    for slot, value in config.equipment.model_dump().items():
        item = catalog.get((slot, value))
        if not item:
            raise HTTPException(422, "La prenda no pertenece a esa categoría.")
        if not item["unlocked"]:
            raise HTTPException(403, f"Todavía no desbloqueaste {item['name']}: {item['requirement']}.")
    player.avatar_config = config.model_dump()
    return wardrobe_state(player)


def prepare_face(image_bytes: bytes) -> bytes:
    """Decode actual pixels, strip metadata and retain only a small stylized crop."""
    if len(image_bytes) > MAX_FACE_BYTES:
        raise HTTPException(413, "La imagen supera los 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(422, "Usá una imagen JPG, PNG o WebP.")
                if getattr(source, "n_frames", 1) != 1:
                    raise HTTPException(422, "La imagen debe ser una foto sin animación.")
                if min(source.size) < 64 or source.width * source.height > MAX_FACE_PIXELS:
                    raise HTTPException(422, "Usá una foto de al menos 64 píxeles y hasta 16 megapíxeles.")
                source.load()
                oriented = ImageOps.exif_transpose(source).convert("RGB")
                face = ImageOps.fit(oriented, (304, 384), method=Image.Resampling.LANCZOS)
                # A gentle local illustration treatment, not AI face reconstruction.
                face = face.filter(ImageFilter.MedianFilter(3))
                face = ImageOps.posterize(face, 5)
                output = BytesIO()
                face.save(output, "PNG", optimize=True)
                return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise HTTPException(422, "No se pudo leer esa foto. Elegí otra imagen.") from error


def save_avatar_face(player, image_bytes: bytes) -> dict:
    if player.is_bot:
        raise HTTPException(403, "Los bots no pueden subir una cara.")
    player.avatar_face = prepare_face(image_bytes)
    player.avatar_face_version = uuid4().hex
    return wardrobe_state(player)


def remove_avatar_face(player) -> dict:
    player.avatar_face = None
    player.avatar_face_version = None
    return wardrobe_state(player)
