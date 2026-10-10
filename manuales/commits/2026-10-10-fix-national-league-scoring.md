# Liga nacional automática con mayoría humana

## Incluido

- La liga nacional UY se acredita de forma implícita cuando los humanos superan
  a los bots en el partido.
- Los jugadores humanos de nacionalidad UY reciben 3 puntos por victoria y 1
  por empate en esa liga, además de cualquier liga adicional asociada al partido.
- Las ligas nacionales no se pueden seleccionar, unir ni administrar
  manualmente.
- Se agrega una comprobación aislada de las reglas, sin conectar ni modificar
  PostgreSQL.

## Release

- Se actualizó `releaser.py` a la versión 2.8.1 porque cambia reglas de
  puntuación distribuidas y recursos estáticos de la Mini App.

## Validación

- `python -m compileall -q src checks/verify_national_league_rules.py`
- `python checks/verify_national_league_rules.py`
- `node --check src/web/match-creator.js`
- `git diff --check`
