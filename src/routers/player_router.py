from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import UploadFile, File

from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session
from src.schemas.player_schema import PlayerResponse, PlayerStatsUpdate, RelatedPlayerResponse
from src.services.player_service import get_player_by_username, update_player_stats, generate_player_card, \
    save_player_photo
from src.database import get_db
from typing import List

router = APIRouter()

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
            punteria=p.punteria,
            velocidad=p.velocidad,
            resistencia=p.resistencia,
            defensa=p.defensa,
            magia=p.magia,
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
            punteria=p.punteria,
            velocidad=p.velocidad,
            resistencia=p.resistencia,
            defensa=p.defensa,
            magia=p.magia,
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
            punteria=p.punteria,
            velocidad=p.velocidad,
            resistencia=p.resistencia,
            defensa=p.defensa,
            magia=p.magia,
            games=games
        )
        for p, games in data
    ]