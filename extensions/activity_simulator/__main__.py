"""Manual runner/status; never initializes a database."""
import argparse
import logging
from pathlib import Path
import time

from dotenv import load_dotenv

from .config import state_path
from .runtime import start
from .storage import Store


def main():
    parser = argparse.ArgumentParser(description="Simulador externo de actividad Maxio")
    parser.add_argument("--status", action="store_true", help="Resumen local sin contraseñas ni acceso a API")
    args = parser.parse_args()
    base = Path(__file__).resolve().parents[2]
    load_dotenv(base / ".env")
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
