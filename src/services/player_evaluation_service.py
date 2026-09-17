from src.models.player_evaluation import PlayerEvaluationPermission
from sqlalchemy.orm import Session
from src.models.match import Match
from src.models.player import Player
from itertools import combinations


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

    # El permiso nace al cerrar el partido y es independiente de los grupos
    # predefinidos. La pareja evaluador -> evaluado es global: la restricción
    # única evita duplicarla si vuelven a jugar antes de evaluarse.
    players = [player for player in match.players if not player.is_bot]

    # Los jugadores que el creador unió explícitamente como un mismo grupo
    # no pueden habilitarse mutuamente para evaluarse en este partido. Esto
    # solo evita crear un permiso nuevo: si ya existía uno de otro partido,
    # permanece intacto.
    grouped_pairs = {
        tuple(sorted((first_id, second_id)))
        for group in (match.pre_set_groups or [])
        for first_id, second_id in combinations(group, 2)
    }

    for evaluator in players:
        for target in players:
            if evaluator.id == target.id:
                continue
            if tuple(sorted((evaluator.id, target.id))) in grouped_pairs:
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
