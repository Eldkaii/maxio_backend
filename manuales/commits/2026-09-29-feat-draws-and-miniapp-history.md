# Empates, resultados y experiencia de la Mini App

## Commit

- Hash: consultar `git log --oneline -1` en la rama que contiene este archivo.
- Mensaje: `feat(matches): add draw results and refine mini app history`

## Incluido

- Empate como resultado completo de partido: votos, cierre, historial, ELO,
  estadísticas de jugador, evaluaciones y rankings de liga.
- Migraciones idempotentes para instalaciones existentes, incluyendo los
  backfills de empates en membresías y rankings.
- Telegram ofrece y registra la respuesta de empate; la Mini App permite
  votarla y la muestra como un resultado válido en historiales y perfiles.
- Correcciones de propiedad y administración de ligas, permisos de evaluación,
  validación de fotos y progresión de estadísticas.
- Mejoras de Mini App: confirmación flotante al enviar una evaluación, acciones
  flotantes no interactivas cuando están ocultas y tarjetas de historial sin
  controles redundantes.

## Release

- Versión actualizada de `2.4.0` a `2.5.0`: se modifican comportamiento de API,
  esquema PostgreSQL, bot de Telegram y recursos estáticos distribuidos.
- `releaser.py` ya empaqueta `src/web/`, imágenes, fuentes y cloudflared; no
  requirió cambios de recursos adicionales.
- No se generó un ejecutable. Un release real debe validar el bundle y no
  distribuir el `.env` copiado actualmente por el script.

## Verificación

- `python -m compileall -q src`
- `git diff --check` sin errores de formato; Git puede advertir conversiones
  CRLF configuradas en el árbol de trabajo.
- La batería de pruebas fue ejecutada y confirmada como correcta por el usuario
  en su entorno aislado. No se ejecutó `pytest` en esta sesión porque el runner
  actual puede ejecutar `drop_all()` contra la base indicada por `.env`.
