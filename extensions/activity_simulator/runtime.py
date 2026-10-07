"""Optional worker lifecycle; the simulator never imports the main application."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
import time

import httpx

from .api import Api
from .config import Config, state_path
from .engine import Engine, UncertainAction
from .storage import Store

log = logging.getLogger("maxio.simulator")


def configure_logging(path):
    """Keep a separate UTF-8 activity log, bounded to four files of 5 MiB."""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    for handler in log.handlers:
        if isinstance(handler, RotatingFileHandler) and handler.baseFilename == str(path):
            return handler
    handler = RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s",
                                           datefmt="%Y-%m-%d %H:%M:%S"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    return handler


class Worker:
    def __init__(self, config, path):
        self.config, self.path = config, path
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name="activity-simulator", daemon=True)

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.stop_event.set()
        # Don't block server shutdown during a stuck network request. The journal
        # remains durable even if the process terminates before its response.
        self.thread.join(timeout=2)

    def run(self):
        api = None
        try:
            store = Store(self.path)
            with store.lock():
                api = Api(self.config.api_url)
                engine = Engine(self.config, store, api, time.time())
                log.info("Simulador activo: máximo %s cuentas; estado persistente local", self.config.max_players)
                while not self.stop_event.is_set():
                    try:
                        # Wait for the HTTP listener, and retry temporary read failures.
                        api.request("GET", "/maxio")
                        engine.tick(time.time())
                    except httpx.HTTPError:
                        log.warning("Simulador: API temporalmente no disponible; reintento en el próximo ciclo")
                    if self.stop_event.wait(max(0.1, self.config.tick_seconds / self.config.speed_multiplier)):
                        break
        except UncertainAction:
            log.error("Simulador pausado: escritura sin confirmación. Revisar el diario local; no se repetirá automáticamente.")
        except Exception as error:
            # Never log response bodies, credentials, tokens or entire state.
            log.error("Simulador detenido (%s); la aplicación continúa normalmente", type(error).__name__)
        finally:
            if api:
                api.close()
            log.info("Worker del simulador finalizado")


def start(base):
    configure_logging(Path(base) / "logs" / "activity-simulator.log")
    return Worker(Config.from_env(), state_path(base)).start()
