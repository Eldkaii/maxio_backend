from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.schemas.auth_schema import LoginRequest, TelegramWebAppAuthRequest, TokenResponse
from src.services.auth_service import authenticate_user, create_access_token
from src.database import get_db  # suponiendo que tenés esta dependencia
from src.services.telegram_identity_service import get_identity_by_telegram_user_id
from src.services.telegram_webapp_service import validate_init_data

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data.username, login_data.password)
    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token)


@router.post("/telegram/webapp", response_model=TokenResponse)
def login_from_telegram_webapp(
    payload: TelegramWebAppAuthRequest,
    db: Session = Depends(get_db),
):
    """Inicia sesión con la identidad Telegram ya vinculada al usuario.

    ``init_data`` está firmado por Telegram y sólo es aceptado durante 24 h;
    no se confía en ningún ID enviado directamente por la Mini App.
    """
    telegram_user = validate_init_data(payload.init_data)
    identity = get_identity_by_telegram_user_id(db, telegram_user["id"])
    if identity is None or identity.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tu cuenta de Telegram todavía no está vinculada a una cuenta de Maxio.",
        )
    token = create_access_token(
        {"sub": identity.user.username},
        expires_delta=timedelta(hours=24),
    )
    return TokenResponse(access_token=token)
