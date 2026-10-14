# Auditoría de adhesión a ligas en administración

## Incluido

- El resumen administrativo incorpora una gráfica de adhesiones de jugadores a
  ligas: membresías totales, membresías con al menos un partido asociado y
  membresías sin participación.
- El desglose por jugador muestra cuántas ligas tiene unidas sobre el total de
  ligas creadas, y cuántas de esas uniones carecen de partido asociado.
- La auditoría excluye bots y el perfil de administración global. Considera una
  membresía utilizada desde que el jugador fue convocado a un partido de esa
  liga, incluso si el partido sigue programado.

## Release

- La revisión integral confirmó que estas métricas y su UI se distribuyen en el
  ejecutable; `releaser.py` queda en la versión 2.8.4 para este commit.

## Validación

- `python -m compileall -q src/services/admin_dashboard_service.py`
- `node --check src/web/admin.js`
- `node checks/verify-admin.cjs` en 1440 px, 390 px y 320 px
- `git diff --check`
