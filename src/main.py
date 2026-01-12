# src/main.py
import threading

from fastapi import FastAPI
import uvicorn

from src.api_clients import notifications_api
from src.database import init_db
from src.utils.logger_config import app_logger as logger
from src.routers import user_router, player_router, match_router, auth_router
from src.database import SessionLocal
from src.utils.init_bots import create_bot_players
from src.utils.seed_initial_data import seed_users_and_players, seed_player_relations
from bot.telegram_bot import run_bot

app = FastAPI()

# Registrar rutas
app.include_router(auth_router.router)
app.include_router(user_router.router, prefix="/maxio")
app.include_router(player_router.router, prefix="/player")
app.include_router(match_router.router, prefix="/match")

# Agregar el router de notificaciones
app.include_router(notifications_api.router, prefix="/notifications")

@app.get("/maxio")
def home():
    return {"message": "API corriendo correctamente"}

@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        create_bot_players(db)
        seed_users_and_players(db)
        seed_player_relations(db)
    finally:
        db.close()

    # 🔹 Levantar el bot en un hilo daemon
    threading.Thread(target=run_bot, daemon=True).start()


def main():
    logger.info("Inicializando base de datos...")
    init_db()
    logger.info("Base de datos lista.")

    logger.info("Levantando servidor FastAPI en http://127.0.0.1:8000...")

    # bot_thread = threading.Thread(
    #     target=run_bot,
    #     daemon=True
    # )
    #
    # bot_thread.start()
    # 🔥 PRIMERO levantamos uvicorn
    # 🔥 DESPUÉS el bot
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
