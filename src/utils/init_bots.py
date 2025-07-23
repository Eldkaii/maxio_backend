from src.models.player import Player
from sqlalchemy.orm import  Session

# al iniciar el sistema o con un script de seeding

def create_bot_players(db: Session, total_bots: int = 20):
    existing_bots = db.query(Player).filter(Player.is_bot == True).count()
    if existing_bots >= total_bots:
        return  # Ya hay suficientes bots, no hace falta crear

    for i in range(existing_bots, total_bots):
        bot = Player(name=f"Bot_{i+1}", is_bot=True)
        db.add(bot)
    db.commit()
