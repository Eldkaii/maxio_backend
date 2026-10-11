from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.news_service import global_news


router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
def list_global_news(
    limit: int = Query(12, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Platform-wide events suitable for the Mini App ticker."""
    return {"items": global_news(db, limit)}
