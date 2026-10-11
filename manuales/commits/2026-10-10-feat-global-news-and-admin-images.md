# Noticias globales e imágenes desde administración

## Incluido

- La barra de la Mini App consume un feed global de resultados, empates,
  premios obtenidos y próximos partidos.
- Se añade `GET /news` como endpoint de sólo lectura para ese feed.
- Administración lista correctamente las imágenes de premios también dentro del
  ejecutable y valida que el archivo elegido pertenezca al catálogo.
- El alta administrativa de un jugador permite elegir y cargar una foto.

## Release

- Se actualizó `releaser.py` a la versión 2.8.2 porque se incorporan endpoint,
  comportamiento de la Mini App y flujos administrativos distribuidos.

## Validación

- `python -m compileall -q src`
- `node --check src/web/club-app.js`
- `node --check src/web/admin.js`
- `node checks/verify-club.cjs vitrina`
- `node checks/verify-admin.cjs`
- `git diff --check`
