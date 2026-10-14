# Niveles de actividad de jugadores en administración

## Incluido

- Se incorporó una gráfica porcentual que distribuye todos los jugadores reales
  según el uso que puede medirse con los datos ya persistidos.
- **Inicial:** no tiene partidos asociados; **Partidos:** tiene al menos un
  partido y ninguna vinculación de liga; **Completo:** tiene partidos y además
  se unió o creó al menos una liga.
- El desglose permite revisar cada jugador junto con su cantidad de partidos,
  ligas unidas y ligas creadas.
- Las tablas de auditoría del resumen se muestran contraídas inicialmente para
  conservar la lectura de los indicadores; se despliegan bajo demanda.

## Release

- La revisión integral confirmó que estas métricas y su UI se distribuyen en el
  ejecutable; `releaser.py` queda en la versión 2.8.4 para este commit.

## Validación

- `python -m compileall -q src/services/admin_dashboard_service.py`
- `node --check src/web/admin.js`
- `node checks/verify-admin.cjs` en 1440 px, 390 px y 320 px
- `git diff --check`
