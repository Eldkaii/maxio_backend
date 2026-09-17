from sqlalchemy import Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from src.database import Base


class PlayerEvaluationRecord(Base):
    """Historial inmutable de una evaluación completada."""

    __tablename__ = "player_evaluation_records"

    id = Column(Integer, primary_key=True)
    evaluator_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    evaluator = relationship("Player", foreign_keys=[evaluator_id], back_populates="evaluations_made")
    target = relationship("Player", foreign_keys=[target_id], back_populates="evaluations_received")
