# Vestuario y recorrido del jugador

El vestuario reemplaza la cancha evolutiva del perfil propio y público. La escena
HTML/CSS contiene cuatro espacios de indumentaria, banco, jugador estático y una
vitrina vacía con estantes para logros, medallas, trofeos y copas.

## Indumentaria

`FullPlayerInfo.locker_room` expone los artículos del catálogo existente mediante
`locker_room_service.py`. No cambia reglas de desbloqueo, estadísticas ni tablas.
Las prendas iniciales y los tatuajes no se exhiben en los percheros: un jugador
nuevo comienza con ellos vacíos, aunque el avatar lleva su ropa genérica.
Sólo se cuelgan artículos que el servidor marca como desbloqueados, respetando
también la afinidad del club. El detalle desplegable muestra requisitos y avance.
Las prendas anteriores se reconocen desde la primera consulta del perfil.

La escena usa el avatar y la indumentaria guardados actualmente. Las poses,
actividades, avatares de amigos y selección aleatoria de ropa quedan para una
etapa posterior. El editor que ya existía sigue disponible en Personalizar.
No se asignan premios físicos a la vitrina hasta definir sus reglas de obtención.

## Historial

Los títulos de participación se conservan a los 1, 5, 10, 25, 50 y 100 partidos.
También se conservan los hitos de victorias y relaciones humanas. Se presentan
como historial, sin prometer tribunas, focos, murales ni trofeos nuevos.
El ELO sigue midiendo rendimiento de forma independiente. Los bots no tienen
vestuario ni carrera. Los hitos se recalculan con los contadores reales: no son
un registro inmutable y no se inventan fechas de obtención.

## Verificación segura

- `python -m unittest discover -s checks -v`: reglas puras de carrera y vestuario.
- `node checks/verify-career.cjs`: Chrome con perfiles ficticios y catálogo real,
  sin arrancar la aplicación ni acceder a PostgreSQL. Comprueba 320–1440 px,
  percheros vacíos y llenos, afinidad, vitrina, perfil público, nombres largos,
  entradas escapadas, refresco, personalización y creación de partidos.
- Capturas locales: `tools/ui-review/career/`, fuera del versionado.
- Compilación Python, sintaxis JavaScript y `git diff --check`.

No se ejecuta pytest ni se comprueba integración con la base real.

## Release

El cambio afecta comportamiento distribuible. `releaser.py` ya incluye todo
`src/web` y no requiere nuevas dependencias. No se crea commit ni ejecutable en
esta entrega; VERSION conserva 2.5.1 y debe avanzar al preparar el commit/release.
