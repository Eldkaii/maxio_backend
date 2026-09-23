# Confiabilidad de Mini App y experiencia de partidos

## Commit

- Hash: consultar `git log --oneline -1` en la rama que contiene este archivo.
- Mensaje: `feat(miniapp): improve Telegram access and match experience`

## Objetivo

Hacer más confiable el acceso de la Mini App desde Telegram durante desarrollo
con Cloudflare Tunnel y mejorar la creación y presentación de partidos.

## Incluido

- Validación pública de DNS y HTTPS antes de publicar una URL temporal de
  Cloudflare; `/start` entrega un botón efímero recién comprobado y comunica
  cuando el enlace todavía está propagándose.
- Inicio de sesión automático en la Mini App para identidades Telegram ya
  vinculadas, con validación criptográfica de `initData` y token de hasta 24 h.
- Balanceo de más de dos grupos prearmados cuando caben en la capacidad final;
  los bots completan los cupos restantes y se rechazan grupos físicamente
  imposibles antes de crear el partido desde la interfaz.
- Estadística OVR en el perfil y mejoras visuales del detalle de los últimos
  partidos: equipos equilibrados, estado ganador/perdedor y tarjetas compactas.
- Contexto versionado para agentes de IA mediante `AGENTS.md` y la skill local
  `skills/maxio-project/`.
- Cambios acumulados de ligas, ranking y recursos visuales presentes en la rama.

## Listo y verificado

- `python -m compileall -q src` ejecutado correctamente.
- Comprobación pública de DNS y HTTPS realizada contra el Quick Tunnel activo.
- `git diff --check` ejecutado; informó únicamente una línea en blanco final
  en `releaser.py`, sin impacto funcional.

## Pendiente

- Un Quick Tunnel siempre genera un hostname temporal; para disponibilidad
  estable en todos los accesos de Telegram se requiere un túnel nombrado y una
  URL pública permanente.
- Las pruebas de integración deben ejecutarse contra una base aislada: el
  fixture actual de pytest puede afectar la base configurada en `.env`.
