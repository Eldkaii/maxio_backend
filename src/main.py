# src/main.py
import threading
import importlib
import os
import sys
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api_clients import notifications_api
from src.database import init_db, SessionLocal
from src.utils.logger_config import app_logger as logger
from src.routers import user_router, player_router, match_router, auth_router, league_router
from src.routers import whatsapp_router
from src.routers import avatar_router
from src.utils.init_bots import create_bot_players
from src.utils.seed_initial_data import seed_users_and_players, seed_player_relations
from src.bot.telegram_bot import run_bot
from src.services.cloudflare_tunnel_service import CloudflareTunnelService
from src.services.league_service import ensure_country_leagues
from src.services.admin_service import ensure_global_admin
from src.config import BASE_DIR

app = FastAPI()

# =========================
# Routers
# =========================
app.include_router(auth_router.router)
app.include_router(user_router.router, prefix="/maxio")
app.include_router(player_router.router, prefix="/player")
app.include_router(avatar_router.router)
app.include_router(match_router.router, prefix="/match")
app.include_router(league_router.router)
app.include_router(notifications_api.router, prefix="/notifications")
app.include_router(whatsapp_router.router)

@app.get("/web/admin", include_in_schema=False)
def admin_home():
    return RedirectResponse(url="/web/admin.html")

@app.get("/web/player", include_in_schema=False)
def player_home():
    return RedirectResponse(url="/web/player-dashboard.html")

app.mount("/web", StaticFiles(directory=BASE_DIR / "web", html=True), name="web")
app.mount("/images", StaticFiles(directory=BASE_DIR / "images"), name="images")

@app.get("/", include_in_schema=False)
def web_home():
    return RedirectResponse(url="/web/")

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
        ensure_global_admin(db)
        create_bot_players(db)
        seed_users_and_players(db)
        seed_player_relations(db)
        ensure_country_leagues(db, "UY")
        db.commit()
    finally:
        db.close()

    # Optional extension kept outside src/ and absent from normal releases.
    # src.config has already loaded .env before this point.
    if os.getenv("SIMULATOR_ENABLED", "false").strip().lower() in {"true", "1", "yes"}:
        try:
            base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
            if str(base) not in sys.path:
                sys.path.insert(0, str(base))
            extension = importlib.import_module("extensions.activity_simulator.runtime")
            app.state.activity_simulator = extension.start(base)
        except Exception as error:
            logger.error("No se pudo iniciar la extensión simuladora (%s)", type(error).__name__)


@app.on_event("shutdown")
async def stop_activity_simulator():
    worker = getattr(app.state, "activity_simulator", None)
    if worker:
        worker.stop()

# =========================
# Main entrypoint
# =========================
def main():
    logger.info("Inicializando base de datos...")
    init_db()

    tunnel = CloudflareTunnelService()
    web_app_url = tunnel.start_for_test_environment()

    logger.info("Iniciando bot de Telegram...")
    bot_thread = threading.Thread(
        target=run_bot,
        args=(web_app_url, tunnel.is_temporary),
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
    finally:
        tunnel.stop()

if __name__ == "__main__":
    main()
