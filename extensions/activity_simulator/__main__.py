"""Manual runner/status; never initializes a database."""
import argparse
import logging
from pathlib import Path
import time

from dotenv import load_dotenv

from .config import Config, state_path
from .api import Api
from .engine import Engine
from .runtime import start, configure_logging
from .storage import Store


def main():
    parser = argparse.ArgumentParser(description="Simulador externo de actividad Maxio")
    parser.add_argument("--status", action="store_true", help="Resumen local sin contraseñas ni acceso a API")
    parser.add_argument("--recover", action="store_true", help="Verifica una adhesión pendiente por GET, respalda y recupera el diario sin reenviar POST")
    args = parser.parse_args()
    base = Path(__file__).resolve().parents[2]
    load_dotenv(base / ".env")
    if args.recover:
        config = Config.from_env()
        configure_logging(base / "logs" / "activity-simulator.log")
        store = Store(state_path(base))
        with store.lock():
            data = store.load()
            if not data or not data.get("journal"):
                print("No hay diario pendiente.")
                return
            if data["api_url"] != config.api_url:
                raise ValueError("El estado pertenece a otra API")
            store.backup()
            api = Api(config.api_url)
            try:
                engine = Engine(config, store, api, time.time())
                if "response" in engine.state["journal"]:
                    logging.getLogger("maxio.simulator").info("Recuperación verificada: diario con respuesta confirmada; pendiente de reanudar el worker")
                    print("La respuesta ya está confirmada; se retomará al iniciar el worker.")
                elif engine.recover_pending_join():
                    print("Membresía verificada por API. Respaldo local creado y respuesta confirmada; no se enviaron POST. Reiniciar el worker para continuar.")
                else:
                    print("No se pudo confirmar la operación. El diario sigue pendiente; no se enviaron POST.")
            finally:
                api.close()
        return
    if args.status:
        data = Store(state_path(base)).load()
        if not data:
            print("Sin estado: el simulador todavía no se inició.")
            return
        jobs = data["jobs"]
        print(f'Cuentas: {sum(a["registered"] for a in data["actors"].values())}; ligas propias: {len(data["leagues"])}')
        for status in ("pending", "done", "blocked", "cancelled"):
            print(f'{status}: {sum(j["status"] == status for j in jobs)}')
        print(f'Escritura por resolver: {bool(data["journal"] and "response" not in data["journal"])}')
        return
    logging.basicConfig(level=logging.INFO)
    worker = start(base)
    try:
        while worker.thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":
    main()
