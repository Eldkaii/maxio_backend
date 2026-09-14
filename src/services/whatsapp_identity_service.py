from sqlalchemy.orm import Session

from src.models.whatsapp_identity import WhatsAppIdentity
from src.models.whatsapp_session import WhatsAppSession


def get_or_create_identity(db: Session, wa_id: str, profile_name: str | None = None) -> WhatsAppIdentity:
    identity = (
        db.query(WhatsAppIdentity)
        .filter(WhatsAppIdentity.wa_id == wa_id, WhatsAppIdentity.is_active.is_(True))
        .first()
    )
    if identity:
        if profile_name and identity.profile_name != profile_name:
            identity.profile_name = profile_name
            db.commit()
        return identity

    identity = WhatsAppIdentity(wa_id=wa_id, profile_name=profile_name, is_active=True)
    db.add(identity)
    db.commit()
    db.refresh(identity)
    return identity


def get_or_create_session(db: Session, identity: WhatsAppIdentity) -> WhatsAppSession:
    session = db.query(WhatsAppSession).filter(WhatsAppSession.identity_id == identity.id).first()
    if session:
        return session

    session = WhatsAppSession(identity_id=identity.id, state="idle", data={})
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def link_identity_to_user(db: Session, identity: WhatsAppIdentity, user) -> WhatsAppIdentity:
    if identity.user_id is not None:
        raise ValueError("Este número de WhatsApp ya está vinculado a un usuario.")
    existing = (
        db.query(WhatsAppIdentity)
        .filter(WhatsAppIdentity.user_id == user.id, WhatsAppIdentity.is_active.is_(True))
        .first()
    )
    if existing:
        raise ValueError("Este usuario ya está vinculado a otro número de WhatsApp.")

    identity.user_id = user.id
    db.commit()
    db.refresh(identity)
    return identity


def unlink_identity_from_user(db: Session, identity: WhatsAppIdentity) -> WhatsAppIdentity:
    identity.user_id = None
    db.commit()
    db.refresh(identity)
    return identity
