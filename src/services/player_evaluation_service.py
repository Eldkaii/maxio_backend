from src.models.player_evaluation import PlayerEvaluationPermission
from sqlalchemy.orm import Session
from src.models.match import Match
from src.models.player import Player
from src.services.match_service import get_player_groups_from_match


def can_player_evaluate(
    db: Session,
    player_id: int,
    target_id: int
) -> bool:
    return db.query(PlayerEvaluationPermission).filter_by(
        evaluator_id=player_id,
        target_id=target_id
    ).first() is not None


def grant_evaluation_permission(
    db: Session,
    evaluator_id: int,
    target_id: int
):
    if evaluator_id == target_id:
        return

    exists = db.query(PlayerEvaluationPermission).filter_by(
        evaluator_id=evaluator_id,
        target_id=target_id
    ).first()

    if not exists:
        db.add(
            PlayerEvaluationPermission(
                evaluator_id=evaluator_id,
                target_id=target_id
            )
        )



def create_evaluation_permissions_from_match(
    db: Session,
    match_id: int
):
    match = db.get(Match, match_id)
    if not match:
        return

    player_groups, _ = get_player_groups_from_match(match, db)

    # Flatten de jugadores (grupos + individuales)
    players: list[Player] = [
        player
        for group in player_groups
        for player in group
    ]

    for evaluator in players:
        for target in players:
            if evaluator.id == target.id:
                continue

            exists = db.query(PlayerEvaluationPermission).filter_by(
                evaluator_id=evaluator.id,
                target_id=target.id
            ).first()

            if not exists:
                db.add(
                    PlayerEvaluationPermission(
                        evaluator_id=evaluator.id,
                        target_id=target.id
                    )
                )

    db.commit()