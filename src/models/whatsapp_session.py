from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import Base


class WhatsAppSession(Base):
    """Estado persistente de un flujo conversacional de WhatsApp."""

    __tablename__ = "whatsapp_sessions"

    id = Column(Integer, primary_key=True, index=True)
    identity_id = Column(
        Integer, ForeignKey("whatsapp_identities.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    state = Column(String(64), nullable=False, default="idle")
    data = Column(JSON, nullable=False, default=dict)
    last_inbound_message_id = Column(String(255), nullable=True, unique=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    identity = relationship("WhatsAppIdentity", lazy="joined")
