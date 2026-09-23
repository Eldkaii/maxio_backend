"""Verificación de disponibilidad pública de la Mini App."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import httpx

from src.utils.logger_config import app_logger as logger


async def public_web_app_is_ready(web_app_url: str, attempts: int = 6) -> bool:
    """Comprueba DNS público y una carga HTTPS antes de publicar una URL.

    Los Quick Tunnels anuncian su hostname antes de que esté propagado. La
    consulta DoH evita considerar como listo un dominio que sólo resuelve en la
    caché DNS local del proceso.
    """
    hostname = urlparse(web_app_url).hostname
    if not hostname:
        return False

    for attempt in range(1, attempts + 1):
        try:
            await asyncio.get_running_loop().getaddrinfo(hostname, 443)
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=5,
                trust_env=False,
            ) as client:
                dns_response = await client.get(
                    "https://cloudflare-dns.com/dns-query",
                    params={"name": hostname, "type": "A"},
                    headers={"accept": "application/dns-json"},
                )
                dns_response.raise_for_status()
                if not dns_response.json().get("Answer"):
                    raise OSError("Cloudflare DNS aún no publicó el hostname")

                response = await client.get(web_app_url)
            if response.is_success:
                return True
            logger.warning(
                "Mini App readiness check %s/%s returned HTTP %s",
                attempt,
                attempts,
                response.status_code,
            )
        except (httpx.HTTPError, OSError, ValueError) as error:
            logger.warning(
                "Mini App readiness check %s/%s failed: %s",
                attempt,
                attempts,
                error,
            )
        if attempt < attempts:
            await asyncio.sleep(2)
    return False
