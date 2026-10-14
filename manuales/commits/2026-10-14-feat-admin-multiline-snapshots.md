# Series multilineales con snapshots administrativos

## Incluido

- El panel administrativo conserva una medición agregada diaria para mostrar
  tendencias reales, sin reconstruir información histórica inexistente.
- Cada indicador usa series independientes: jugadores, partidos, ligas,
  adhesiones, niveles de actividad y premios/logros.
- Las ligas activas ahora requieren al menos un partido ya jugado dentro de su
  calendario vigente.
- El gráfico aclara que la serie comienza en la primera medición disponible;
  los datos previos no se simulan.

## Release

- El cambio modifica funcionalidades del ejecutable y agrega el modelo de
  snapshots que se crea de forma aditiva mediante `Base.metadata.create_all`.
  Se incrementó `releaser.py` a la versión 2.8.5.

## Validación

- `python -m compileall -q src/services/admin_dashboard_service.py src/models/admin_metric_snapshot.py`
- `node --check src/web/admin.js`
- `node checks/verify-admin.cjs` en 1440 px, 390 px y 320 px
- `git diff --check`
