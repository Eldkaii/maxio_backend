"""Read-only, paginated histories for the three-screen club interface."""
from sqlalchemy import case, or_
from src.models import Match, MatchPlayer, Player, TeamEnum
from src.models.player import PlayerRelation


def serialize_player_matches(db, player, associations):
    recent_matches = []
    for assoc in associations:
        match = assoc.match
        my_team = assoc.team

        # Las respuestas se comparten entre la notificación y la mini-app:
        # una única fila por usuario/partido representa la respuesta enviada.
        from src.models import MatchResultReply
        replies = {
            reply.user_id: reply.result
            for reply in db.query(MatchResultReply).filter(
                MatchResultReply.match_id == match.id
            ).all()
        }

        teammates = [{
            "id": player.id,
            "name": player.name,
            "response": "bot" if player.is_bot else replies.get(player.user_id, "pending"),
        }]
        opponents = []

        for mp in match.match_associations:
            if mp.player_id == player.id:
                continue
            entry = {
                "id": mp.player.id,
                "name": mp.player.name,
                "response": "bot" if mp.player.is_bot else replies.get(mp.player.user_id, "pending"),
            }
            if mp.team == my_team:
                teammates.append(entry)
            else:
                opponents.append(entry)

        # Determinar resultado del partido
        if match.is_draw:
            result = "draw"
        elif match.winner_team_id is None or my_team is None:
            result = "pending"  # Partido aún no tiene resultado
        elif (
            (my_team == TeamEnum.team1 and match.winner_team_id == match.team1_id) or
            (my_team == TeamEnum.team2 and match.winner_team_id == match.team2_id)
        ):
            result = "win"
        else:
            result = "loss"

        recent_matches.append({
            "match_id": match.id,
            "date": match.date.isoformat(),  # Convertimos a string
            "team": my_team.value if my_team else None,
            "result": result,
            "my_response": "bot" if player.is_bot else replies.get(player.user_id, "pending"),
            "teammates": teammates,
            "opponents": opponents,
        })


    return recent_matches


def player_match_history(db, player, offset=0, limit=20):
    associations = (
        db.query(MatchPlayer).join(Match, MatchPlayer.match_id == Match.id)
        .filter(MatchPlayer.player_id == player.id)
        .order_by(Match.date.desc(), Match.id.desc())
        .offset(offset).limit(limit + 1).all()
    )
    return {
        "items": serialize_player_matches(db, player, associations[:limit]),
        "has_more": len(associations) > limit,
        "next_offset": offset + min(len(associations), limit),
    }


def player_connection_history(db, player, offset=0, limit=20):
    other_id = case(
        (PlayerRelation.player1_id == player.id, PlayerRelation.player2_id),
        else_=PlayerRelation.player1_id,
    )
    total = PlayerRelation.games_together + PlayerRelation.games_apart
    rows = (
        db.query(Player.name, PlayerRelation.games_together, PlayerRelation.games_apart)
        .join(PlayerRelation, Player.id == other_id)
        .filter(or_(PlayerRelation.player1_id == player.id,
                    PlayerRelation.player2_id == player.id),
                Player.is_bot.is_(False), total > 0)
        .order_by(total.desc(), Player.id.asc())
        .offset(offset).limit(limit + 1).all()
    )
    return {
        "items": [dict(name=r.name, games_together=r.games_together,
                       games_apart=r.games_apart,
                       total_games=r.games_together + r.games_apart)
                  for r in rows[:limit]],
        "has_more": len(rows) > limit,
        "next_offset": offset + min(len(rows), limit),
    }
