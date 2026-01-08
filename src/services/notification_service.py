from datetime import datetime
from sqlalchemy.orm import Session
from src.models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: int,
    event_type: str,
    channel: str,
    payload: dict,
    available_at: datetime | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        event_type=event_type,
        channel=channel,
        payload=payload,
        status="pending",
        available_at=available_at or datetime.utcnow(),
    )

    db.add(notification)
    return notification

def create_notifications_for_users(
    db: Session,
    *,
    user_ids: list[int],
    event_type: str,
    channel: str,
    payload_factory: callable,
    available_at: datetime | None = None,
) -> None:
    """
    payload_factory: función que recibe user_id y devuelve el payload
    """

    for user_id in user_ids:
        create_notification(
            db,
            user_id=user_id,
            event_type=event_type,
            channel=channel,
            payload=payload_factory(user_id),
            available_at=available_at,
        )
