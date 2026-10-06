from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
import os


@dataclass(frozen=True)
class Config:
    api_url: str = "http://127.0.0.1:8000"
    max_players: int = 40
    signup_min_hours: float = 2
    signup_max_hours: float = 8
    startup_delay_seconds: float = 300
    tick_seconds: float = 30

    @classmethod
    def from_env(cls):
        config = cls(
            api_url=os.getenv("SIMULATOR_API_URL", cls.api_url).rstrip("/"),
            max_players=int(os.getenv("SIMULATOR_MAX_PLAYERS", "40")),
            signup_min_hours=float(os.getenv("SIMULATOR_SIGNUP_MIN_HOURS", "2")),
            signup_max_hours=float(os.getenv("SIMULATOR_SIGNUP_MAX_HOURS", "8")),
            startup_delay_seconds=float(os.getenv("SIMULATOR_STARTUP_DELAY_SECONDS", "300")),
            tick_seconds=float(os.getenv("SIMULATOR_TICK_SECONDS", "30")),
        )
        parsed = urlsplit(config.api_url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("SIMULATOR_API_URL debe apuntar a la API local")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("SIMULATOR_API_URL debe ser un origen local sin credenciales ni ruta")
        if not 10 <= config.max_players <= 500:
            raise ValueError("SIMULATOR_MAX_PLAYERS debe estar entre 10 y 500")
        if not 0 < config.signup_min_hours <= config.signup_max_hours:
            raise ValueError("Intervalos de registro inválidos")
        if config.tick_seconds < 1 or config.startup_delay_seconds < 0:
            raise ValueError("Intervalos del simulador inválidos")
        return config


def state_path(base: Path) -> Path:
    return Path(os.getenv("SIMULATOR_STATE_PATH", str(base / ".local" / "activity-simulator.json"))).resolve()
