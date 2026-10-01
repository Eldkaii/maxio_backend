# Rediseño visual del perfil de jugador

## Commit

- Hash: consultar git log --oneline -1 en la rama que contiene este archivo.
- Mensaje: feat(web): redesign player profile and avatar skill views

## Incluido

- Nueva presentación visual del perfil de jugador y sus métricas.
- Dos vistas de habilidades: tarjetas integradas y mapa corporal del avatar.
- Animaciones secuenciales para avatar, conectores y habilidades al abrir la
  vista Avatar, tanto en web como en la Mini App.
- Diseño específico y escalado proporcional del mapa corporal para pantallas
  de la Mini App.
- Historial de partidos con resultado destacado, equipos simétricos y expansión
  al pulsar la tarjeta.
- Avatares base y variantes de indumentaria normalizados a 1024x1536 y
  disponibles en el selector de escritorio.

## Release

- Versión actualizada de 2.5.0 a 2.5.1: se modifican recursos estáticos y
  comportamiento distribuido de la Mini App.
- releaser.py ya empaqueta src/web/, imágenes y fuentes; no requirió cambios
  adicionales de empaquetado.
- No se generó un ejecutable en esta sesión.

## Verificación

- python -m compileall -q src
- git diff --check
- Comprobación estática de llaves CSS y existencia/dimensiones de los assets
  de avatar.
- No se ejecutó pytest: su configuración actual puede ejecutar drop_all()
  contra la base configurada.
