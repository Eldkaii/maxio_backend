# Centro de control administrativo

Commit: `28cbb7a` — `feat(admin): add control center and safe simulator recovery`

## Cambios

- Rediseño de `/web/admin`: navegación por resumen, jugadores, partidos,
  ligas, premios y simulador; diseño adaptable a escritorio y móvil.
- Cuatro métricas principales y cuatro gráficas diarias con períodos de
  7, 30, 90 y 365 días, valores por punto y tablas accesibles.
- Explorador con búsqueda por nombre/ID, paginación de 20 registros y
  fichas enlazadas entre jugadores, partidos, ligas y destinatarios de premios.
- Los detalles incluyen estadísticas, convocados/equipos/votos, rankings,
  últimas 100 partidas o entregas y condiciones de premios, según la entidad.
  Todos los partidos siguen disponibles en el listado paginado global.
- Formularios para crear jugadores, partidos, ligas con fechas obligatorias,
  logros y trofeos. Se conserva edición de premios y vista previa de su imagen.
- Simulador con log seguro como texto, errores resaltados, límite de registros
  y actualización automática cada 15 segundos.
- Servicios de lectura y endpoints protegidos por administrador global.
  Las respuestas de jugadores seleccionan campos deportivos explícitos;
  no serializan cuentas ni credenciales.
- Corrección de creación de ligas por administrador sin perfil deportivo:
  no exige ni crea una membresía ficticia.

## Interpretación de las gráficas

El esquema actual no conserva fechas de alta de jugadores ni de ligas y los
partidos guardan fecha de encuentro, no de creación. No se inventan datos:

- Jugadores: debut en un encuentro finalizado y humanos activos por día.
- Partidos: encuentros programados/finalizados por fecha del encuentro.
- Ligas: inicio de temporada y ligas con partidos finalizados por día.
- Premios: definiciones creadas y entregas registradas por sus timestamps.

Las gráficas explican esas definiciones. Se excluyen fechas futuras; el período
incluye el día actual y usa UTC. Las métricas de portada son totales actuales,
excepto humanos activos, que corresponde al período seleccionado.

## Verificación

- `node --check src/web/admin.js`.
- Compilación Python de servicios/router modificados.
- `checks/verify_admin_queries.py`: compilación PostgreSQL sin conexión ni
  ejecución SQL; series vacías, permisos admin y creación de liga sin jugador.
- `checks/verify-admin.cjs`: Chrome headless con API sintética, 1440/390/320 px;
  navegación, cuatro tipos de detalle, búsqueda, paginación, creación de los
  cuatro modelos, edición de premios, fechas enviadas, errores, estados vacíos,
  log, contenido escapado y desbordes. Capturas en `tools/ui-review/admin/`.
- Revisión visual de escritorio y móvil. `git diff --check`.
- No se arrancó la aplicación ni se ejecutó pytest o SQL contra la base real.
  La integración con datos persistidos queda fuera de esta verificación aislada.

## Release

`releaser.py`: versión **2.8.0**, por cambio de interfaz y comportamiento
distribuible. La regla existente incluye `src/web/` completo, incluido el nuevo
`admin.css`. Sin dependencias nuevas ni cambios de esquema. No se generó ni
distribuyó ejecutable; no se creó commit.
