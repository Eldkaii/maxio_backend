from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi import FastAPI
from sqlalchemy.orm import Session
from typing import Literal
from src.schemas.user_schema import AdminPlayerCreate, UserCreate, UserResponse
from pydantic import BaseModel, constr
from src.schemas.auth_schema import TelegramWebAppLinkRequest
from src.services.user_service import create_user
from src.database import get_db
from src.services.auth_service import get_current_user
from src.services.telegram_identity_service import create_identity_if_not_exists, link_identity_to_user
from src.services.telegram_webapp_service import validate_init_data
from src.services.league_service import sync_player_country_league
from src.services.admin_service import create_player_as_admin, get_admin_summary, require_global_admin
from src.services.simulator_log_service import read_simulator_log
from src.services.admin_dashboard_service import dashboard_metrics, list_entities, entity_detail
from src.services.achievement_definition_service import list_definitions, serialize, trophy_images
from src.models import AchievementDefinition


from src.utils.logger_config import app_logger as logger

app = FastAPI()

router = APIRouter(prefix="/users", tags=["Users"])

class UserProfileUpdate(BaseModel):
    first_name: str = ""
    last_name: str = ""
    nationality: constr(min_length=2, max_length=2) = "UY"


class AchievementDefinitionPayload(BaseModel):
    key: constr(min_length=2, max_length=80)
    name: constr(min_length=2, max_length=120)
    description: str = ""
    conditions: dict[str, float] = {}
    trophy_image: str | None = None
    reward_type: Literal["achievement", "trophy"] | None = None
    active: bool = True

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
        ,"is_admin": current_user.is_admin
    }


@router.get("/admin/summary")
def admin_summary(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_global_admin(current_user)
    return get_admin_summary(db)


@router.get("/admin/dashboard")
def admin_dashboard(days: int = Query(30, ge=7, le=365), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_global_admin(current_user)
    return dashboard_metrics(db, days)


@router.get("/admin/entities/{kind}")
def admin_entities(kind: Literal["players", "matches", "leagues", "awards"], search: str = Query("", max_length=100), page: int = Query(1, ge=1), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_global_admin(current_user)
    return list_entities(db, kind, search.strip(), page)


@router.get("/admin/entities/{kind}/{entity_id}")
def admin_entity(kind: Literal["players", "matches", "leagues", "awards"], entity_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_global_admin(current_user)
    return entity_detail(db, kind, entity_id)


@router.get("/admin/achievements")
def admin_achievements(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_global_admin(current_user)
    return {"items": list_definitions(db), "trophies": trophy_images()}


@router.post("/admin/achievements")
def admin_create_achievement(payload: AchievementDefinitionPayload, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_global_admin(current_user)
    if db.query(AchievementDefinition).filter_by(key=payload.key).first():
        raise HTTPException(status_code=409, detail="Ya existe un logro con esa clave.")
    item = AchievementDefinition(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return serialize(item)


@router.put("/admin/achievements/{achievement_id}")
def admin_update_achievement(achievement_id: int, payload: AchievementDefinitionPayload, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_global_admin(current_user)
    item = db.get(AchievementDefinition, achievement_id)
    if not item:
        raise HTTPException(status_code=404, detail="Logro no encontrado.")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit(); db.refresh(item)
    return serialize(item)


@router.post("/admin/players", response_model=UserResponse, status_code=201)
def admin_create_player(
    payload: AdminPlayerCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_global_admin(current_user)
    try:
        return create_player_as_admin(db, payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/admin/simulator/log")
def admin_simulator_log(
    response: Response,
    limit: int = Query(default=200, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    require_global_admin(current_user)
    response.headers["Cache-Control"] = "no-store"
    try:
        return read_simulator_log(limit)
    except OSError as error:
        raise HTTPException(status_code=503, detail="No se pudo leer el log del simulador.") from error


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
