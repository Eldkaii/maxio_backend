# src/main.py
import threading
import uvicorn
from fastapi import FastAPI

from src.api_clients import notifications_api
from src.database import init_db, SessionLocal
from src.utils.logger_config import app_logger as logger
from src.routers import user_router, player_router, match_router, auth_router
from src.utils.init_bots import create_bot_players
from src.utils.seed_initial_data import seed_users_and_players, seed_player_relations
from src.bot.telegram_bot import run_bot

app = FastAPI()

# =========================
# Routers
# =========================
app.include_router(auth_router.router)
app.include_router(user_router.router, prefix="/maxio")
app.include_router(player_router.router, prefix="/player")
app.include_router(match_router.router, prefix="/match")
app.include_router(notifications_api.router, prefix="/notifications")

@app.get("/maxio")
def home():
    return {"message": "API corriendo correctamente"}

# =========================
# Startup logic (NO BOT)
# =========================
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        create_bot_players(db)
        seed_users_and_players(db)
        seed_player_relations(db)
    finally:
        db.close()

# =========================
# Main entrypoint
# =========================
def main():
    logger.info("Inicializando base de datos...")
    init_db()

    logger.info("Iniciando bot de Telegram...")
    bot_thread = threading.Thread(
        target=run_bot,
        daemon=True
    )
    bot_thread.start()

    logger.info("Levantando servidor FastAPI...")
    try:
        uvicorn.run(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Maxio detenido manualmente")

if __name__ == "__main__":
    main()
