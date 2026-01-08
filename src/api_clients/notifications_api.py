# src/api_clients/notifications_api.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from src.database import get_db
from src.notification.notification_dispatcher import dispatch_pending_notifications

router = APIRouter()


@router.post("/send-pending-notifications")
def send_pending_notifications_post(db: Session = Depends(get_db)):
    """
    Endpoint POST para enviar notificaciones pendientes.
    """
    try:
        processed = dispatch_pending_notifications(db)  # ⚡ función sincrónica
        return {"processed": processed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/send-pending-notifications")
def send_pending_notifications_get(db: Session = Depends(get_db)):
    """
    Endpoint GET para enviar notificaciones pendientes.
    """
    try:
        processed = dispatch_pending_notifications(db, now=datetime.utcnow())  # ⚡ sin await
        return {"processed": processed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
