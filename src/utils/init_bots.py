from pathlib import Path

from sqlalchemy.orm import Session

from src.config import BASE_DIR
from src.models.player import Player

# al iniciar el sistema o con un script de seeding

def _bot_names() -> list[str]:
    names_file = BASE_DIR / "bots_name"
    names = [line.strip() for line in names_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(names) < 50:
        raise ValueError("bots_name debe contener al menos 50 nombres.")
    return names[:50]


def create_bot_players(db: Session, total_bots: int | None = None):
    names = _bot_names()
    total_bots = total_bots or len(names)
    if total_bots > len(names):
        raise ValueError("No hay nombres suficientes en bots_name para crear los bots solicitados.")

    faces = sorted((BASE_DIR / "images" / "random_faces").glob("*"))
    if not faces:
        raise ValueError("No se encontraron caras en images/random_faces.")

    bots = db.query(Player).filter(Player.is_bot.is_(True)).order_by(Player.id).all()
    for index, bot in enumerate(bots[:total_bots]):
        bot.name = names[index]
        bot.photo_path = str(faces[index % len(faces)].resolve())

    for index in range(len(bots), total_bots):
        db.add(Player(
            name=names[index],
            is_bot=True,
            photo_path=str(faces[index % len(faces)].resolve()),
        ))
    db.commit()
