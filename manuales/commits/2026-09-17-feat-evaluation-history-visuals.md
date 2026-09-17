# Evaluaciones e historial visual de la Mini App

## Commit

- Hash: consultar `git log --oneline -1` en la rama que contiene este archivo.
- Mensaje: `feat(web): improve evaluations and history navigation`

## Objetivo

Mejorar la experiencia visual de las evaluaciones y del historial de relaciones,
manteniendo los permisos de evaluación de un solo uso y mostrando su historial.

## Incluido

- Evaluación mediante barras deslizables, con selección individual de estadísticas.
- Selector visual con pelota de fútbol, marcado por defecto y estado atenuado al desmarcarlo.
- Registro persistente de evaluaciones realizadas y contador por jugador.
- Corrección de la dirección del contador: muestra cuántas veces el perfil visitado evaluó al usuario actual.
- Corrección del consumo de permisos para evitar que reaparezcan al abrir un perfil.
- Historial de relaciones contraído detrás de un botón de tres barras azul, verde y rojo.
- Animación de apertura y cierre del historial, con brillo y colores translúcidos.
- Separación visual entre evaluaciones pendientes y el historial.
- Modelo y tabla `player_evaluation_records` para conservar el historial de evaluaciones.

## Listo y verificado

- `python -m compileall -q src` ejecutado correctamente.
- Tests de permisos y perfiles ejecutados correctamente: 5 tests exitosos.
- `git diff --check` sin errores.

## Consideraciones

- La tabla de historial se crea automáticamente al iniciar la aplicación mediante `init_db`.
- La validación visual final debe realizarse en Telegram Mini App y en pantallas pequeñas.

## Pendiente

- Validación manual final de las transiciones en distintos WebViews móviles.
