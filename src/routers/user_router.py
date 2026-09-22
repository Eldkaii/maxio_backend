from fastapi import APIRouter, Depends, HTTPException
from fastapi import FastAPI
from sqlalchemy.orm import Session
from src.schemas.user_schema import UserCreate, UserResponse
from pydantic import BaseModel, constr
from src.schemas.auth_schema import TelegramWebAppLinkRequest
from src.services.user_service import create_user
from src.database import get_db
from src.services.auth_service import get_current_user
from src.services.telegram_identity_service import create_identity_if_not_exists, link_identity_to_user
from src.services.telegram_webapp_service import validate_init_data
from src.services.league_service import sync_player_country_league


from src.utils.logger_config import app_logger as logger

app = FastAPI()

router = APIRouter(prefix="/users", tags=["Users"])

class UserProfileUpdate(BaseModel):
    first_name: str = ""
    last_name: str = ""
    nationality: constr(min_length=2, max_length=2) = "UY"

@router.post("/telegram/link")
def link_telegram_webapp(
    payload: TelegramWebAppLinkRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    telegram_user = validate_init_data(payload.init_data)
    identity = create_identity_if_not_exists(
        db,
        telegram_user_id=telegram_user["id"],
        telegram_username=telegram_user.get("username"),
    )
    if identity.user_id is not None and identity.user_id != current_user.id:
        raise HTTPException(status_code=409, detail="Esta cuenta de Telegram ya está vinculada a otro usuario.")
    if identity.user_id is None:
        try:
            link_identity_to_user(db, identity, current_user)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error))
    return {"linked": True, "telegram_user_id": telegram_user["id"]}

@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        new_user = create_user(user, db, stats=user.stats)
        return new_user
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception("Error inesperado al registrar usuario")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/me")
def read_current_user(current_user: UserResponse = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "id": current_user.id
        ,"first_name": current_user.first_name
        ,"last_name": current_user.last_name
        ,"nationality": current_user.nationality
    }

@router.put("/me/profile")
def update_current_profile(
    payload: UserProfileUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.first_name = payload.first_name.strip()
    current_user.last_name = payload.last_name.strip()
    current_user.nationality = payload.nationality.upper()
    if current_user.player and not current_user.player.is_bot:
        sync_player_country_league(db, current_user.player, current_user.nationality)
    db.commit()
    return {"first_name": current_user.first_name, "last_name": current_user.last_name, "nationality": current_user.nationality}
