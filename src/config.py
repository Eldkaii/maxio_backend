# src/config.py
import os
from dotenv import load_dotenv
from pathlib import Path


# Carga el archivo .env
load_dotenv()

class Settings:
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    DATABASE_URL = (
        f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    BASE_DIR = Path(__file__).resolve().parent
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    API_BASE_PATH: str = os.getenv("API_BASE_PATH", "/maxio")

    API_CARD_TEMPLATE_PATH = BASE_DIR / "images" / "template_player_card.png"
    API_MATCH_TEMPLATE_PATH = BASE_DIR / "images" / "template_match_card.png"
    API_MATCH_TEMPLATE_RELATIONS_PATH = BASE_DIR / "images" / "template_match_card_relations.png"

    API_PHOTO_PLAYER_PATH_FOLDER = BASE_DIR / "images" / "player_photos"
    API_ICONS_MATCH_PATH_FOLDER = BASE_DIR / "images" / "icons"

    DEFAULT_PHOTO_PATH =  BASE_DIR / "images" / "no_face_image"/ "no_face.png"
    DEFAULT_FONTS_PATH =  BASE_DIR / "fonts"


    @property
    def api_root(self) -> str:
        return f"{self.API_BASE_URL.rstrip('/')}{self.API_BASE_PATH}"

    @property
    def api_root_login(self) -> str:
        return f"{self.API_BASE_URL.rstrip('/')}"


settings = Settings()