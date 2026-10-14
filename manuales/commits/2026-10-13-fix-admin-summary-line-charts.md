# Gráficos de línea en el resumen administrativo

## Incluido

- Los indicadores operativos de jugadores, partidos, ligas y premios ahora se
  representan como gráficos de línea con puntos, valores y grilla horizontal.
- Las tablas de desglose de ligas y premios se mantienen sin cambios.
- Se actualizaron las versiones de los recursos estáticos para evitar que el
  navegador conserve los gráficos de barras anteriores en caché.

## Release

- Se actualizó `releaser.py` a la versión 2.8.4 porque el ejecutable distribuye
  esta modificación visual del panel administrativo.

## Validación

- `node --check src/web/admin.js`
- `node checks/verify-admin.cjs` en 1440 px, 390 px y 320 px, con el mismo
  contrato `summary` que devuelve el dashboard.
- `git diff --check`
