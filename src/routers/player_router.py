from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import UploadFile, File

from fastapi.responses import FileResponse, StreamingResponse

from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.schemas.player_full_profile_schema import FullPlayerInfo
from src.schemas.player_schema import CustomBotCreate, PlayerResponse, PlayerStatsUpdate, RelatedPlayerResponse
from src.services.player_service import get_player_by_username, update_player_stats, generate_player_card, \
    save_player_photo, build_full_player_profile, create_custom_bot, suggest_custom_bot_name
from src.database import get_db
from src.models import Player, User
from src.config import settings
from src.services.auth_service import get_current_user
from pathlib import Path
from typing import List

router = APIRouter()


@router.get("/directory", response_model=List[PlayerResponse], tags=["players"])
def player_directory(
    query: str = Query("", max_length=60),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Directorio de jugadores reales para los selectores de la web."""
    players = db.query(Player).outerjoin(User, Player.user_id == User.id).filter(
        Player.is_bot.is_(False),
        or_(User.id.is_(None), User.is_admin.is_(False)),
    )
    if query.strip():
        term = f"%{query.strip()}%"
        players = players.filter(or_(
            Player.name.ilike(term),
            User.first_name.ilike(term),
            User.last_name.ilike(term),
        ))
    return players.order_by(
        Player.cant_partidos.desc(),
        Player.name.asc(),
    ).limit(limit).all()


@router.post("/bots", response_model=PlayerResponse, tags=["players"])
def create_bot(
    payload: CustomBotCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Crea el bot diseñado en la Mini App antes de asociarlo al partido."""
    try:
        return create_custom_bot(payload.name, payload.model_dump(exclude={"name"}), db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/bots/name", tags=["players"])
def suggest_bot_name(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return {"name": suggest_custom_bot_name(db)}

@router.get("/{username}", response_model=PlayerResponse, tags=["players"])
def read_player(username: str, db: Session = Depends(get_db)):
    try:
        player = get_player_by_username(username, db)
        return player
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{username}/card", tags=["players"])
def get_player_card(username: str, db: Session = Depends(get_db)):
    try:
        buffer = generate_player_card(username, db)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="image/png"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{target_username}/stats", tags=["players"])
def set_player_stats(
    target_username: str,
    evaluator_username: str,
    stats: PlayerStatsUpdate,
    db: Session = Depends(get_db)
):
    try:
        updated_player = update_player_stats(
            target_username=target_username,
            evaluator_username=evaluator_username,
            stats_data=stats,
            db=db
        )
        return {"message": "Stats actualizados correctamente", "player": updated_player.name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{username}/profile", response_model=FullPlayerInfo)
def get_player_profile(username: str, db: Session = Depends(get_db)):
    try:
        profile = build_full_player_profile(db, username)
        return profile
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{username}/photo", tags=["players"])
def get_player_photo(username: str, db: Session = Depends(get_db)):
    try:
        player = get_player_by_username(username, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    photo = Path(player.photo_path) if player.photo_path else settings.DEFAULT_PHOTO_PATH
    if not photo.is_file():
        photo = settings.DEFAULT_PHOTO_PATH
    return FileResponse(photo)

@router.post("/{username}/photo")
async def upload_player_photo(
    username: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 🛑 Validar tipo de archivo
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen"
        )

    # 📦 Leer bytes
    image_bytes = await file.read()

    # 🛑 Validar tamaño (5 MB)
    MAX_SIZE = 5 * 1024 * 1024
    if len(image_bytes) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail="La imagen supera el tamaño máximo permitido (5MB)"
        )

    try:
        photo_filename = save_player_photo(
            username=username,
            image_bytes=image_bytes,
            filename=file.filename,
            db=db
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    return {
        "username": username,
        "photo": photo_filename,
        "message": "Foto subida correctamente"
    }


@router.get("/{username}/top_teammates", response_model=List[RelatedPlayerResponse])
def get_top_teammates(
    username: str,
    limit: int = Query(5, ge=1, le=20),
    exclude_bots: bool = Query(False),
    db: Session = Depends(get_db)
):
    try:
        player = get_player_by_username(username, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    data = player.top_teammates(db, limit=limit, exclude_bots=exclude_bots)
    return [
        RelatedPlayerResponse(
            id=p.id,
            name=p.name,
            cant_partidos=p.cant_partidos,
            elo=p.elo,
            tiro=p.tiro,
            ritmo=p.ritmo,
            fisico=p.fisico,
            defensa=p.defensa,
            aura=p.aura,
            games=games
        )
        for p, games in data
    ]

@router.get("/{username}/top_allies", response_model=List[RelatedPlayerResponse])
def get_top_allies(
    username: str,
    limit: int = Query(3, ge=1, le=20),
    exclude_bots: bool = Query(False),
    db: Session = Depends(get_db)
):
    try:
        player = get_player_by_username(username, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    data = player.top_allies(db, limit=limit, exclude_bots=exclude_bots)
    return [
        RelatedPlayerResponse(
            id=p.id,
            name=p.name,
            cant_partidos=p.cant_partidos,
            elo=p.elo,
            tiro=p.tiro,
            ritmo=p.ritmo,
            fisico=p.fisico,
            defensa=p.defensa,
            aura=p.aura,
            games=games
        )
        for p, games in data
    ]


@router.get("/{username}/top_opponents", response_model=List[RelatedPlayerResponse])
def get_top_opponents(
    username: str,
    limit: int = Query(3, ge=1, le=20),
    exclude_bots: bool = Query(False),
    db: Session = Depends(get_db)
):
    try:
        player = get_player_by_username(username, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    data = player.top_opponents(db, limit=limit, exclude_bots=exclude_bots)
    return [
        RelatedPlayerResponse(
            id=p.id,
            name=p.name,
            cant_partidos=p.cant_partidos,
            elo=p.elo,
            tiro=p.tiro,
            ritmo=p.ritmo,
            fisico=p.fisico,
            defensa=p.defensa,
            aura=p.aura,
            games=games
        )
        for p, games in data
    ]
