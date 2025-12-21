# src/config.py
import os
from dotenv import load_dotenv

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

    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    API_BASE_PATH: str = os.getenv("API_BASE_PATH", "/maxio")

    @property
    def api_root(self) -> str:
        return f"{self.API_BASE_URL.rstrip('/')}{self.API_BASE_PATH}"

    @property
    def api_root_login(self) -> str:
        return f"{self.API_BASE_URL.rstrip('/')}"


settings = Settings()