# Mini App, perfiles y registro de jugadores

## Commit

- Hash: consultar `git log --oneline -1` en la rama que contiene este archivo.
- Mensaje: `feat(web): complete miniapp profiles, avatars and registration`

## Objetivo

Consolidar la evolución de la Mini App de Telegram y la web de Maxio,
incluyendo perfiles de jugadores, avatares, creación de partidos, historial,
registro de usuarios y acceso directo desde Telegram.

## Incluido

- Mini App web con login, registro de nuevos jugadores e inicio de sesión automático.
- Vinculación de la cuenta con Telegram al autenticarse desde la Mini App.
- Perfiles propios y públicos con nombre, apellido, nacionalidad y bandera.
- Edición de avatar desde galería y cámara, con silueta y normalización a 408x466 PNG RGBA.
- Cromo animado del jugador en perfiles propios y públicos.
- Historial reciente limitado a tres partidos, detalle ampliado y respuestas de resultado.
- Historial de relaciones compacto, expandible por cada una de sus tres áreas.
- Creación de partidos desde la Mini App con selección de jugadores, equipos y bots.
- Correcciones visuales de tarjetas, nombres, navegación y botón Volver.
- Configuración del botón de Mini App en Telegram y respuesta de `/start` con acceso directo.
- Integración de bots con nombres e imágenes de caras aleatorias.
- Ajustes de túnel Cloudflare, persistencia de usuarios y modelos de perfil.

## Listo y verificado

- `python -m compileall -q src` ejecutado correctamente con el entorno del proyecto.
- `git diff --check` sin errores de espacios en blanco.
- Normalización de imágenes probada con una imagen de ejemplo y salida 408x466 RGBA.

## Consideraciones

- El acceso directo desde `/start` requiere que el túnel HTTPS esté disponible.
- Telegram continúa enviando técnicamente el evento `/start`, pero el usuario recibe
  un botón para abrir la Mini App en lugar de atravesar el flujo conversacional.
- El proyecto contiene archivos visuales y datos de prueba propios del entorno local.

## Pendiente

- Validación visual final en Android/Telegram con el túnel activo.
- Pruebas de integración completas contra una base de datos limpia.
