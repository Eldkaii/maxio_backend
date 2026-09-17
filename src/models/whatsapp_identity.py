from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import Base


class WhatsAppIdentity(Base):
    """Identidad de WhatsApp vinculable a un usuario de Max_io."""

    __tablename__ = "whatsapp_identities"

    id = Column(Integer, primary_key=True, index=True)
    wa_id = Column(String(32), unique=True, nullable=False, index=True)
    profile_name = Column(String(100), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", lazy="joined")

