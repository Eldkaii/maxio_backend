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

# =========================
# Cargar .env de forma estricta
# =========================
ENV_PATH = Path(".env")

if not ENV_PATH.exists():
    print("❌ ERROR: Archivo .env no encontrado")
    print("👉 Debe existir un archivo .env junto al ejecutable")
    sys.exit(1)

if not load_dotenv(dotenv_path=ENV_PATH):
    print("❌ ERROR: No se pudo cargar el archivo .env")
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
