# Simulador opcional de actividad

Extensión externa al código de producto (`extensions/`, fuera de `src/`). Consume
la misma API HTTP que la Mini App, con las credenciales de cada cuenta sintética.
No importa modelos, servicios ni configuración del backend y no escribe SQL.
El único enlace en la aplicación es el arranque/parada opcional en `src/main.py`.

## Activación

En el `.env` del proyecto se agregaron las opciones con el simulador apagado:

```env
SIMULATOR_ENABLED=true
SIMULATOR_MAX_PLAYERS=40
SIMULATOR_SIGNUP_MIN_HOURS=2
SIMULATOR_SIGNUP_MAX_HOURS=8
SIMULATOR_STARTUP_DELAY_SECONDS=300
SIMULATOR_SPEED_MULTIPLIER=1
```

Reiniciar la aplicación de la manera habitual. Con `false` o sin variable no se
importa ni arranca la extensión. Detener la aplicación detiene también su worker;
las acciones futuras permanecen en disco. El arranque también funciona usando
`uvicorn src.main:app` siempre que la base ya esté inicializada.

`.env.example` contiene las opciones adicionales de URL local, intervalo del
worker y ubicación del estado. `SIMULATOR_SPEED_MULTIPLIER=1` conserva los
intervalos normales; un valor `3` reduce aproximadamente a un tercio las
esperas de registros, planificación, actividad social, ligas, partidos y votos.
También acelera el intervalo de consulta del worker. El límite de partidos por
jugador se mantiene proporcional al reloj simulado.

También se puede ejecutar por separado, desde la raíz del repositorio:

```powershell
.venv\Scripts\python.exe -m extensions.activity_simulator
.venv\Scripts\python.exe -m extensions.activity_simulator --status
```

La ejecución manual es una activación explícita, independientemente de la bandera
de arranque automático. `--status` sólo lee el estado y muestra conteos, sin API
ni contraseñas. Un bloqueo del sistema operativo impide dos workers sobre el mismo
archivo de estado. Usar siempre el mismo archivo para la misma instalación.

## Actividad

- Primera alta a los cinco minutos; durante el arranque inicial se incorporan las
  primeras diez cuentas cada 10–30 minutos y luego se vuelve a una cadencia de
  2–8 horas aleatorias a velocidad 1, hasta 40 por defecto. Los nombres y apellidos se toman de
  `src/1000_nombres_apellidos_espana_latinoamerica.txt`; los usernames combinan
  partes del nombre y apellido y ocasionalmente agregan números.
  Son nombres ficticios verosímiles, usernames variados,
  nacionalidad UY, emails reservados `@example.com`, contraseñas aleatorias y stats
  iniciales variadas. Son cuentas de usuario con `is_bot=false`, necesarias para
  votar y puntuar. Su pertenencia al simulador está registrada en el estado local.
- Visitas de perfil espaciadas entre uno y tres días. Preferencia por convocar a
  quienes ya compartieron partidos, con algo de rotación.
- Fútbol 5, diez participantes exclusivamente creados por esta extensión; fechas
  futuras entre las 18:00 y las 22:30 de Uruguay (UTC−3). Se reserva la cuota al
  planificar para evitar que dos partidos futuros excedan el límite.
- Cada persona tiene un objetivo/límite de uno o dos partidos en cualquier ventana
  de siete días. Se cuentan **todos los partidos en los que participa**, tanto los
  que organiza como aquellos a los que otro jugador simulado la agrega. La cuota
  es individual, incluye reservas futuras y se conserva al reiniciar. Puede jugar
  menos si no hay diez personas disponibles o la app
  estuvo apagada. Nunca se inventa un partido pasado para compensar inactividad.
- Convocatorias, grupos de 2–4 compañeros y balanceo por los endpoints existentes.
  Las invitaciones al partido se distribuyen en pasos separados por 2–8 minutos.
- Entre 90 y 150 minutos después del comienzo se inicia la votación. Cada persona
  informa victoria o derrota desde su equipo real asignado, o empate; el resto de
  los votos se espacian. No se asignan ganadores ni puntos directamente.
- Aproximadamente el 25% tiene predisposición a organizar una liga, después de
  unas seis horas de actividad a velocidad 1 y con diez cuentas disponibles. La creación se
  agenda para los siguientes 30–90 minutos. Los nombres se toman de
  `src/ligas_nombres.txt`. Hay un tope aproximado de una liga por cada diez
  personas (mínimo una posible). Sólo algunas personas se incorporan, en días
  sucesivos, con preferencia por las ligas de compañeros frecuentes. No se une a
  ligas ajenas al simulador; la nacional UY se asigna por el registro normal.
- No existe un endpoint de amistad en el producto actual. Los círculos sociales
  se modelan como afinidades en la agenda; `PlayerRelation` crece de verdad cuando
  la aplicación cierra los partidos compartidos.

**Cierre de partidos:** el POST de resultados registra votos; el dispatcher
existente de Maxio es quien cierra el encuentro y actualiza estadísticas,
relaciones y rankings. Actualmente ese dispatcher corre en el worker de Telegram.
Si Telegram no inició su worker, los votos pueden quedar pendientes de cierre
hasta que éste funcione. Esta extensión no inicia Telegram ni suplanta su worker.
Las cuentas sintéticas no vinculan Telegram/WhatsApp ni reciben mensajes externos.

## Log de actividad

Al arrancar se crea `logs/activity-simulator.log`, en UTF-8, con fecha y hora local,
nivel y detalle de cada acción: alta de usuario, confirmación/visita de perfil,
planificación y creación de partido, cada convocatoria, grupos, balanceo, cada
voto, actualización de afinidades locales, creación de liga y adhesión a una liga.
Se identifican los usernames, partidos y ligas involucrados, más la acción/paso
para localizarla en el estado. También se registran cancelaciones, reintentos,
bloqueos, fallos y el inicio/finalización del worker.

Los éxitos se escriben después de confirmar la respuesta y guardar el estado;
una escritura de resultado incierto se registra como interrupción, nunca como
éxito. El log es operativo: el diario persistente sigue siendo la referencia de
recuperación si el proceso cae entre guardar el estado y escribir el mensaje.
No incluye contraseñas, tokens, emails ni cuerpos de las peticiones/respuestas.
Rota a los 5 MiB y conserva tres archivos anteriores (`.1`, `.2`, `.3`).
`logs/` está excluido de Git.

También se puede consultar desde **Administración → Actividad del simulador**.
El panel permite ver los últimos 100, 200 o 500 registros, actualizar manualmente
o refrescar cada 15 segundos. Incluye los archivos rotados para completar la
cantidad solicitada, hasta un máximo de 256 KiB leídos por consulta. Conserva
el historial visible aunque el simulador esté apagado. La lectura se realiza por
`GET /maxio/users/admin/simulator/log`, exclusivamente para administradores
autenticados; los logs no se publican como archivos estáticos.

Para seguir las acciones en vivo desde PowerShell:

```powershell
Get-Content -Encoding UTF8 .\logs\activity-simulator.log -Tail 30 -Wait
```

## Persistencia y recuperación

Las adhesiones a ligas que quedan sin respuesta se verifican al arrancar mediante
`GET /leagues/{id}`. Sólo si la API confirma el ID del jugador entre los miembros
se guarda la confirmación y se completa el paso local, sin repetir el POST.
Si la membresía no aparece, la lectura falla o la operación es de otro tipo,
el diario conserva su protección contra reenvíos inciertos.

Para confirmar una adhesión pendiente sin iniciar actividad adicional:

```powershell
.venv\Scripts\python.exe -m extensions.activity_simulator --recover
```

Este comando toma el bloqueo exclusivo, crea un respaldo local `.recovery-*.bak`
junto al estado y consulta la API. No ejecuta POST ni inicia el worker. El respaldo
contiene el mismo estado sensible que el original: no compartirlo ni versionarlo.
Después de recuperar, reiniciar el worker de la manera habitual. Las nuevas
escrituras inciertas conservan en `journal.failure` el tipo de excepción y el
código HTTP, cuando exista, sin mensajes/cuerpos que puedan contener secretos.

`.local/activity-simulator.json` guarda cuentas, contraseñas, reservas, ligas,
afinidades y acciones. `.local/` está excluido de Git. No compartir ese archivo;
en Windows hereda los permisos del directorio de usuario/proyecto. Se escribe
mediante reemplazo atómico y se mantiene un diario antes/después de cada POST.

Una respuesta confirmada se retoma después de un reinicio sin reenviar el POST.
Ante un timeout de escritura, error de servidor o caída antes de confirmar el
checkpoint, el worker se pausa y deja `journal` pendiente: los endpoints heredados
no tienen claves de idempotencia y reenviar podría duplicar usuarios o partidos.
La aplicación principal sigue funcionando. Para recuperarlo, detener el worker,
respaldar el estado y revisar la acción indicada en `journal.path` y `journal.key`
contra la API. Si se confirmó, registrar su respuesta JSON en `journal.response`;
si se verificó que no se ejecutó, poner `journal` en `null` y reiniciar. Nunca
vaciar el diario por intuición. Errores 4xx definitivos bloquean ese trabajo;
401/429 difieren el reintento. No se imprimen credenciales ni cuerpos de errores.

Si la app estuvo apagada, nuevas altas y planes parten del momento actual, sin
recuperar todas las acciones perdidas de golpe. Partidos aún no creados cuya fecha
quedó demasiado cerca se cancelan y liberan reservas. Votaciones atrasadas más de
23 horas se marcan para revisión, porque el producto puede haber aplicado timeout.
Los partidos ya creados se conservan. No hay limpieza automática de datos.

No borrar el estado para reiniciar una población: se perdería la referencia a las
cuentas existentes. Para otra base/API usar un archivo de estado independiente.
Al habilitarlo, los datos sintéticos se registran en la base que sirve esa API,
incluyendo su participación en la liga UY. No confundirlos con usuarios orgánicos
en análisis de adopción.

## Verificación y distribución

```powershell
.venv\Scripts\python.exe checks/test_activity_simulator.py
.venv\Scripts\python.exe -m compileall -q extensions/activity_simulator src/main.py
```

Pruebas unitarias con reloj controlado, API falsa y temporales: actividad de 60 días,
cuotas móviles, votos por equipo, afinidad, ligas, reinicios, diario y exclusión
mutua. No importan `src.database`, no leen `.env`, no levantan servidores ni ejecutan
pytest. No se ejecutó el simulador contra la base local durante la implementación.

No se creó commit ni release. `releaser.py` queda sin cambios porque la extensión
no integra el bundle oficial. El hook usa una importación dinámica; si se necesita
en un ejecutable, distribuir opcionalmente `extensions/` junto al `.exe` con sus
dependencias disponibles, y verificar ese empaquetado por separado. Al preparar
el commit del hook corresponde revisar la versión del ejecutable. El modo fuente
usa `httpx` y `python-dotenv`, que ya son dependencias del proyecto.
