"""Only the authenticated owner can edit an avatar or upload its face."""

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Player, User
from src.schemas.avatar_schema import AvatarConfig, AvatarWardrobe
from src.services.auth_service import get_current_user
from src.services.avatar_service import (
    MAX_FACE_BYTES, remove_avatar_face, save_avatar_config, save_avatar_face, wardrobe_state,
)

router = APIRouter(prefix="/player", tags=["avatar"])


def own_player(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Player:
    # Serialize wardrobe mutations and face replacement for this owner.
    player = db.query(Player).filter(Player.user_id == user.id).with_for_update().first()
    if player is None or player.is_bot:
        raise HTTPException(403, "La cuenta no tiene un jugador habilitado.")
    return player


@router.get("/me/avatar", response_model=AvatarWardrobe)
def get_wardrobe(player: Player = Depends(own_player)):
    return wardrobe_state(player)


@router.put("/me/avatar", response_model=AvatarWardrobe)
def update_wardrobe(payload: AvatarConfig, player: Player = Depends(own_player), db: Session = Depends(get_db)):
    result = save_avatar_config(player, payload)
    db.commit()
    return result


@router.post("/me/avatar/face", response_model=AvatarWardrobe)
def upload_face(file: UploadFile = File(...), player: Player = Depends(own_player), db: Session = Depends(get_db)):
    result = save_avatar_face(player, file.file.read(MAX_FACE_BYTES + 1))
    db.commit()
    return result


@router.delete("/me/avatar/face", response_model=AvatarWardrobe)
def delete_face(player: Player = Depends(own_player), db: Session = Depends(get_db)):
    result = remove_avatar_face(player)
    db.commit()
    return result


@router.get("/{username}/avatar/face")
def get_face(username: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.name == username).first()
    if player is None or not player.avatar_face_version or not player.avatar_face:
        raise HTTPException(404, "Este jugador no tiene una cara cargada.")
    return Response(bytes(player.avatar_face), media_type="image/png", headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })
