# src/config.py

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# =========================
# Base dir compatible EXE
# =========================
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

BASE_DIR = get_base_dir()
PROJECT_DIR = Path(__file__).resolve().parent.parent

# =========================
# Cargar .env de forma estricta
# =========================
ENV_PATH = (
    Path(sys.executable).resolve().parent / ".env"
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent / ".env"
)

if not ENV_PATH.exists():
    print("ERROR: Archivo .env no encontrado")
    print("Debe existir un archivo .env junto al ejecutable o en la raíz del proyecto")
    sys.exit(1)

if not load_dotenv(dotenv_path=ENV_PATH):
    print("ERROR: No se pudo cargar el archivo .env")
    sys.exit(1)

class Settings:
    # =========================
    # Database
    # =========================
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    DATABASE_URL = (
        f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # =========================
    # Telegram
    # =========================
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    # URL pública estable de la Mini App (necesaria al usar un túnel nombrado).
    # Con Quick Tunnel se detecta automáticamente al iniciar la aplicación.
    TELEGRAM_WEB_APP_URL = os.getenv("TELEGRAM_WEB_APP_URL", "").strip()

    # =========================
    # WhatsApp Cloud API
    # =========================
    WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_WABA_ID = os.getenv("WHATSAPP_WABA_ID")
    META_APP_SECRET = os.getenv("META_APP_SECRET")
    WHATSAPP_WEBHOOK_VERIFY_TOKEN = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN")
    WHATSAPP_GRAPH_API_VERSION = os.getenv("WHATSAPP_GRAPH_API_VERSION", "v23.0")
    APP_ENV = os.getenv("APP_ENV", "PROD").upper()
    CLOUDFLARE_TUNNEL_TOKEN = os.getenv("CLOUDFLARE_TUNNEL_TOKEN")
    CLOUDFLARED_PATH = Path(
        os.getenv("CLOUDFLARED_PATH", str(PROJECT_DIR / "tools" / "cloudflared.exe"))
    )

    # =========================
    # API
    # =========================
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    API_BASE_PATH: str = os.getenv("API_BASE_PATH", "/maxio")

    # =========================
    # Paths (todos desde BASE_DIR)
    # =========================
    BASE_DIR = BASE_DIR

    API_CARD_TEMPLATE_PATH = BASE_DIR / "images" / "template_player_card.png"
    API_CARD_TEMPLATE_PATHS = (
        API_CARD_TEMPLATE_PATH,
        BASE_DIR / "images" / "template_player_card_v2.png",
    )
    API_MATCH_TEMPLATE_PATH = BASE_DIR / "images" / "template_match_card.png"
    API_MATCH_TEMPLATE_RELATIONS_PATH = BASE_DIR / "images" / "template_match_card_relations.png"

    API_PHOTO_PLAYER_PATH_FOLDER = BASE_DIR / "images" / "player_photos"
    API_ICONS_MATCH_PATH_FOLDER = BASE_DIR / "images" / "icons"

    DEFAULT_PHOTO_PATH = BASE_DIR / "images" / "no_face_image" / "no_face.png"
    DEFAULT_FONTS_PATH = BASE_DIR / "fonts"

    # =========================
    # Others
    # =========================
    MATCH_RESULT_TIMEOUT_HOURS = 24

    @property
    def api_root(self) -> str:
        return f"{self.API_BASE_URL.rstrip('/')}{self.API_BASE_PATH}"

    @property
    def api_root_login(self) -> str:
        return self.API_BASE_URL.rstrip('/')


settings = Settings()
