"""Proceso local de Cloudflare Tunnel para el modo de pruebas."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from src.config import settings
from src.utils.logger_config import app_logger as logger


class CloudflareTunnelService:
    """Inicia el conector de un túnel nombrado y lo cierra con la aplicación."""

    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None

    def start_for_test_environment(self) -> None:
        if settings.APP_ENV != "TEST":
            return
        executable = Path(settings.CLOUDFLARED_PATH)
        if not executable.is_file():
            logger.warning("Cloudflare Tunnel no iniciado: no existe %s", executable)
            return

        try:
            command = [str(executable), "tunnel", "--no-autoupdate"]
            if settings.CLOUDFLARE_TUNNEL_TOKEN:
                command.extend(["run", "--token", settings.CLOUDFLARE_TUNNEL_TOKEN])
                tunnel_type = "nombrado"
            else:
                command.extend(["--url", "http://localhost:8000"])
                tunnel_type = "rápido"

            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            threading.Thread(target=self._log_output, daemon=True).start()
            logger.info("Cloudflare Tunnel %s iniciado para APP_ENV=TEST", tunnel_type)
        except OSError:
            logger.exception("No se pudo iniciar Cloudflare Tunnel")

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        logger.info("Cloudflare Tunnel detenido")

    def _log_output(self) -> None:
        if not self.process or not self.process.stdout:
            return
        for line in self.process.stdout:
            logger.info("cloudflared: %s", line.rstrip())
