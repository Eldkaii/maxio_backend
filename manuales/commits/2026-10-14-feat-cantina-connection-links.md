# Vínculos de jugadores en Cantina

## Incluido

- Los nombres de compañero, mejor sociedad y rival se integran como enlaces
  centrales de las tarjetas de Cantina.
- Se aplicó jerarquía tipográfica en mayúsculas, sombra cálida y centrado de
  los contadores de partidos, sin añadir fondos ni bordes ajenos a las tarjetas.
- La comprobación visual incorpora relaciones sintéticas para revisar el estado
  con enlaces destacados.

## Release

- La revisión integral confirmó que estos recursos estáticos se distribuyen en
  el ejecutable; `releaser.py` queda en la versión 2.8.4 para este commit.

## Validación

- `node --check src/web/club-app.js`
- `node checks/verify-club.cjs cantina`
- `git diff --check`
