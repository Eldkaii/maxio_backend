# Indicadores operativos en administración

## Incluido

- El panel de jugadores distingue perfiles humanos registrados, quienes no
  participaron todavía y quienes figuran en uno o más partidos, incluidos los
  programados.
- El panel de partidos separa los encuentros finalizados de los programados a
  futuro.
- El panel de ligas informa cuántas existen, cuáles están activas con partidos
  y una tabla de frecuencia de uso por liga para el período elegido.
- El panel de premios muestra el total entregado y los logros o trofeos con más
  entregas.

## Release

- Se actualizó `releaser.py` a la versión 2.8.3 porque el ejecutable distribuye
  el panel administrativo y su comportamiento visible cambió.

## Validación

- `python -m compileall -q src`
- `node --check src/web/admin.js`
- `node checks/verify-admin.cjs`
- `git diff --check`
