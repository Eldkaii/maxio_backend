from fastapi import APIRouter, Depends, HTTPException
from fastapi import FastAPI
from sqlalchemy.orm import Session
from src.schemas.user_schema import UserCreate, UserResponse
from src.services.user_service import create_user
from src.database import get_db

from src.utils.logger_config import app_logger as logger

app = FastAPI()

router = APIRouter(prefix="/users", tags=["Users"])

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


