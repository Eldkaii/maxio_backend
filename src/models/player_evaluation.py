# src/models/player_evaluation_permission.py

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from src.database import Base

class PlayerEvaluationPermission(Base):
    __tablename__ = "player_evaluation_permissions"

    id = Column(Integer, primary_key=True)

    evaluator_id = Column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False
    )
    target_id = Column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "evaluator_id",
            "target_id",
            name="uq_player_evaluation_permission"
        ),
        CheckConstraint(
            "evaluator_id <> target_id",
            name="ck_player_evaluation_not_self"
        ),
    )

    evaluator = relationship(
        "Player",
        foreign_keys=[evaluator_id],
        back_populates="evaluation_permissions_given"
    )

    target = relationship(
        "Player",
        foreign_keys=[target_id],
        back_populates="evaluation_permissions_received"
    )
