# src/scripts/seed_initial_data.py

from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.user import User
from src.models.player import Player, PlayerRelation

from src.scripts.init_los_pibes import INITIAL_USERS
from src.scripts.init_los_pibes import INITIAL_PLAYER_RELATIONS


# -----------------------------
# Helpers
# -----------------------------

def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_player_by_username(db: Session, username: str) -> Player | None:
    user = get_user_by_username(db, username)
    if not user:
        return None
    return user.player


# -----------------------------
# Seed Users + Players
# -----------------------------

def seed_users_and_players(db: Session):
    print("▶ Seeding users and players...")

    for entry in INITIAL_USERS:
        username = entry["username"]
        email = entry["email"]
        password = entry["password"]
        player_data = entry["player"]
        stats = player_data["stats"]

        # Validación fuerte de stats
        for stat in ["tiro", "ritmo", "fisico", "defensa", "aura"]:
            if stats.get(stat) is None:
                raise ValueError(f"Stat '{stat}' missing for user '{username}'")

        user = get_user_by_username(db, username)

        if not user:
            user = User(
                username=username,
                email=email,
            )
            user.set_password(password)
            db.add(user)
            db.flush()  # necesitamos user.id
            print(f"  + User creado: {username}")
        else:
            #print(f"  = User existente: {username}")
            continue

        if not user.player:
            player = Player(
                name=player_data["name"],
                user_id=user.id,
                is_bot=False,
                elo=1000,
                recent_results=[],
                tiro=stats["tiro"],
                ritmo=stats["ritmo"],
                fisico=stats["fisico"],
                defensa=stats["defensa"],
                aura=stats["aura"],
            )
            db.add(player)
            print(f"    + Player creado para {username}")
        else:
            # player = user.player
            # player.name = player_data["name"]
            # player.tiro = stats["tiro"]
            # player.ritmo = stats["ritmo"]
            # player.fisico = stats["fisico"]
            # player.defensa = stats["defensa"]
            # player.aura = stats["aura"]
            # print(f"    = Player actualizado para {username}")
            continue

    db.commit()
    print("✔ Users y Players listos\n")


# -----------------------------
# Seed Player Relations
# -----------------------------

def seed_player_relations(db: Session):
    print("▶ Seeding player relations...")

    for username_a, relations in INITIAL_PLAYER_RELATIONS.items():
        player_a = get_player_by_username(db, username_a)
        if not player_a:
            raise ValueError(f"Player not found for username '{username_a}'")

        for username_b, values in relations.items():
            player_b = get_player_by_username(db, username_b)
            if not player_b:
                raise ValueError(f"Player not found for username '{username_b}'")

            together = values.get("together")
            apart = values.get("apart")

            if together is None or apart is None:
                raise ValueError(
                    f"Missing values for relation {username_a} - {username_b}"
                )

            player1_id, player2_id = sorted([player_a.id, player_b.id])

            relation = (
                db.query(PlayerRelation)
                .filter_by(player1_id=player1_id, player2_id=player2_id)
                .first()
            )

            if not relation:
                relation = PlayerRelation(
                    player1_id=player1_id,
                    player2_id=player2_id,
                )
                db.add(relation)
                print(f"  + Relation creada: {username_a} - {username_b}")
            else:
                #print(f"  = Relation existente: {username_a} - {username_b}")
                break

            # SET directo (idempotente)
            relation.games_together = together
            relation.games_apart = apart

    db.commit()
    print("✔ Player relations listas\n")


# -----------------------------
# Main
# -----------------------------

def run():
    db = SessionLocal()
    try:
        seed_users_and_players(db)
        seed_player_relations(db)
        print("🎉 Seed de datos iniciales completado con éxito")
    finally:
        db.close()


if __name__ == "__main__":
    run()
