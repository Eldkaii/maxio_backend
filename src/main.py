# src/main.py

from fastapi import FastAPI
import uvicorn

from src.database import init_db
from src.utils.logger_config import app_logger as logger
from src.routers import user_router,player_router,match_router
from src.database import SessionLocal
from src.utils.init_bots import create_bot_players

app = FastAPI()

# Registrar rutas
app.include_router(user_router.router, prefix="/maxio")
app.include_router(player_router.router, prefix="/player")
app.include_router(match_router.router, prefix="/match")


@app.get("/maxio")
def home():
    return {"message": "API corriendo correctamente"}

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        create_bot_players(db)
    finally:
        db.close()

def main():
    logger.info("Inicializando base de datos...")
    init_db()
    logger.info("Base de datos lista.")

    logger.info("Levantando servidor FastAPI en http://localhost:8000...")
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
