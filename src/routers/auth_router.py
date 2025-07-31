from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.schemas.auth_schema import LoginRequest, TokenResponse
from src.services.auth_service import authenticate_user, create_access_token
from src.database import get_db  # suponiendo que tenés esta dependencia

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data.username, login_data.password)
    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token)
