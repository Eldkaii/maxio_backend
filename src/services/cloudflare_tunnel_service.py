"""Proceso local de Cloudflare Tunnel para el modo de pruebas."""

from __future__ import annotations

import subprocess
import threading
import re
from pathlib import Path

from src.config import settings
from src.utils.logger_config import app_logger as logger


class CloudflareTunnelService:
    """Inicia el conector de un túnel nombrado y lo cierra con la aplicación."""

    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None
        self.public_url: str | None = None
        self.is_temporary = False
        self._public_url_ready = threading.Event()
        self._tunnel_connected = threading.Event()

    def start_for_test_environment(self) -> str | None:
        if settings.APP_ENV != "TEST":
            return None
        executable = Path(settings.CLOUDFLARED_PATH)
        if not executable.is_file():
            logger.warning("Cloudflare Tunnel no iniciado: no existe %s", executable)
            return None

        try:
            command = [str(executable), "tunnel", "--no-autoupdate"]
            if settings.CLOUDFLARE_TUNNEL_TOKEN:
                command.extend(["run", "--token", settings.CLOUDFLARE_TUNNEL_TOKEN])
                tunnel_type = "nombrado"
            else:
                command.extend(["--url", "http://localhost:8000"])
                self.is_temporary = True
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

            if settings.CLOUDFLARE_TUNNEL_TOKEN:
                self.public_url = settings.TELEGRAM_WEB_APP_URL or None
                if not self.public_url:
                    logger.warning(
                        "Mini App no configurada: definí TELEGRAM_WEB_APP_URL con la URL pública del túnel nombrado"
                    )
                return self._web_url()

            # El Quick Tunnel escribe una URL trycloudflare.com en su salida.
            # Esperar brevemente permite configurar Telegram antes de arrancar el bot.
            if not self._public_url_ready.wait(timeout=15):
                logger.warning("No se obtuvo la URL pública del Quick Tunnel a tiempo")
                return None
            if not self._tunnel_connected.wait(timeout=15):
                logger.warning("El Quick Tunnel no confirmó una conexión pública a tiempo")
                return None
            return self._web_url()
        except OSError:
            logger.exception("No se pudo iniciar Cloudflare Tunnel")
            return None

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
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line, re.IGNORECASE)
            if match and not self.public_url:
                self.public_url = match.group(0)
                self._public_url_ready.set()
                logger.info("URL pública del túnel detectada: %s", self.public_url)
            if "Registered tunnel connection" in line:
                self._tunnel_connected.set()

    def _web_url(self) -> str | None:
        if not self.public_url:
            return None
        return f"{self.public_url.rstrip('/')}/web/"
