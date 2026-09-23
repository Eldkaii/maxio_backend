# Max_io: contexto de proyecto para agentes de IA

## Skill reutilizable

La skill versionada y accesible dentro de este repositorio está en
[`skills/maxio-project/SKILL.md`](skills/maxio-project/SKILL.md). Sus referencias
se leen por área de trabajo y contienen las directivas operativas obligatorias.
Este archivo conserva el contexto completo como lectura de referencia general.

## Propósito

**Max_io** es una plataforma local de fútbol amateur. Permite registrar jugadores,
crear y balancear partidos, completar equipos con bots, registrar resultados,
actualizar estadísticas/ELO y mostrar perfiles con historial de compañeros y
rivales. También ofrece una Mini App de Telegram y flujos conversacionales para
Telegram y WhatsApp.

El usuario final debe poder gestionar su perfil, organizar un partido y consultar
su evolución deportiva desde la Mini App. La API también sirve las imágenes de
tarjetas de jugador y de partido generadas con Pillow.

## Estado y rama de trabajo

- La aplicación está en desarrollo; la rama activa habitual es
  `FEATURE/codex/ligas`.
- Hay una implementación reciente y aún en evolución de **ligas y rankings**.
  No asumir que una modificación no confirmada es descartable: revisar siempre
  `git status` antes de editar.
- El backend usa PostgreSQL. No es compatible con SQLite: `Player.recent_results`
  usa `ARRAY` de PostgreSQL.

## Arquitectura

```text
Telegram Mini App (/web/) ──┐
                            ├── FastAPI ── SQLAlchemy ── PostgreSQL
Bot Telegram (polling) ─────┤
Webhook WhatsApp ───────────┘
                            └── Pillow: tarjetas PNG y fotos

FastAPI puede exponerse a Telegram mediante cloudflared.
```

El único proceso principal es `start.py`, que importa `src.main.main()`.
`main()` inicializa la BD, opcionalmente levanta Cloudflare Tunnel, inicia el bot
en un hilo daemon y ejecuta Uvicorn en el puerto `8000`.

### Capas del backend

| Carpeta | Responsabilidad |
| --- | --- |
| `src/models/` | Entidades SQLAlchemy y relaciones de la base. |
| `src/schemas/` | Contratos Pydantic de requests/responses. |
| `src/services/` | Lógica de negocio. Aquí deben vivir las reglas, no en routers. |
| `src/routers/` | Endpoints FastAPI. `main.py` les aplica prefijos. |
| `src/bot/` | Bot de Telegram, handlers, comandos y conversaciones. |
| `src/notification/` | Despacho de notificaciones y cierre de resultados. |
| `src/web/` | Mini App estática: HTML, CSS y JavaScript sin framework. |
| `src/utils/` | Balanceo, seeds, logging y utilidades. |
| `src/test/` | Pruebas pytest. Ver advertencia crítica abajo. |

## Arranque y configuración

La configuración se carga de forma obligatoria desde `.env` en `src/config.py`.
No imprimir ni versionar secretos. Las variables principales son:

```env
DB_HOST=...
DB_PORT=...
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
TELEGRAM_TOKEN=...
API_BASE_URL=http://127.0.0.1:8000
API_BASE_PATH=/maxio
APP_ENV=TEST|PROD
```

Para WhatsApp se usan `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`,
`WHATSAPP_WABA_ID`, `META_APP_SECRET`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN` y,
opcionalmente, `WHATSAPP_GRAPH_API_VERSION`.

Para Telegram:

- Con `APP_ENV=TEST` y sin `CLOUDFLARE_TUNNEL_TOKEN`, se crea un **Quick Tunnel**
  temporal `*.trycloudflare.com` hacia `http://localhost:8000`.
- Cada reinicio cambia esa URL. Los botones inline antiguos quedan rotos y pueden
  mostrar `net::ERR_NAME_NOT_RESOLVED`; en modo temporal la Mini App se abre sólo
  desde el botón de menú, que el bot actualiza tras verificar la nueva URL.
- Un túnel nombrado usa `CLOUDFLARE_TUNNEL_TOKEN` y requiere
  `TELEGRAM_WEB_APP_URL` con la URL HTTPS pública estable.
- La Mini App se sirve en `/web/`; imágenes y fotos se exponen en `/images/`.

`init_db()` crea tablas y contiene migraciones SQL manuales de compatibilidad.
Antes de modificarlo, considerar que no hay Alembic ni migraciones versionadas.
Agregar cambios de esquema de forma idempotente y segura para bases existentes.

## Modelo de dominio

### Usuarios y jugadores

- `User`: cuenta, email, contraseña BCrypt, nombre/apellido, nacionalidad y
  bandera `is_admin` global.
- `Player`: perfil deportivo 1:1 con `User` (o bot sin usuario), cinco stats
  (`tiro`, `ritmo`, `fisico`, `defensa`, `aura`), ELO, partidos, victorias,
  resultados recientes y foto.
- `PlayerRelation`: relación canónica entre un par de jugadores, contando
  partidos juntos y enfrentados.
- Los bots pueden ser iniciales (seed) o personalizados desde la Mini App; los
  bots ayudan a completar cupos pero no votan resultados ni puntúan rankings.

### Partidos

- `Match`: fecha, capacidad total, dos equipos, ganador, votos, grupos
  predefinidos JSON y liga opcional.
- `MatchPlayer`: asociación de jugador/partido y lado asignado (`team1` o
  `team2`).
- `Team`: lista de jugadores; un partido referencia `team1`, `team2` y
  `winner_team`.
- Se crean convocados, grupos que no deben separarse y luego se balancean los
  humanos. Si faltan lugares, se agregan bots según la lógica de
  `services/match_service.py` y `utils/balance_teams.py`.

Al cerrar un partido, `assign_match_winner()` actualiza historial/ELO, relaciones,
permisos de evaluación y rankings de liga aplicables. El cierre puede ocurrir por
votos completos, resultado irreversible o timeout de 24 h. Las respuestas de
resultado pendientes son procesadas por el dispatcher de notificaciones.

### Ligas y rankings

- `League`: pública/privada, especial, nacional gestionada por sistema, creador,
  país, divisiones y límite opcional de tamaño de grupo.
- `LeagueMember`: rol `member` o `admin` por liga.
- `LeagueRanking`: cada miembro tiene `general`, `solo_duo` y `grupo`, con puntos,
  partidos, victorias, derrotas, racha y pin.
- Los administradores globales gestionan cualquier liga; propietario y admins de
  liga gestionan la propia.
- Un usuario normal puede crear hasta tres ligas. Las nacionales (actualmente
  Uruguay) se sincronizan para jugadores humanos de esa nacionalidad y no se
  pueden abandonar.
- Un partido de liga puede tener invitados, pero solamente miembros de esa liga
  reciben puntos. Los miembros de la nacional UY también se actualizan cuando
  corresponda.

Las reglas y serialización están en `services/league_service.py`; la actualización
de puntos se encuentra en `services/match_service.py`.

## Superficie HTTP

Prefijos finales definidos en `src/main.py`:

| Ruta | Uso |
| --- | --- |
| `/` | Redirige a `/web/`. |
| `/auth/login` | Login JWT. |
| `/maxio/users/register`, `/maxio/users/me` | Registro y perfil de cuenta. |
| `/maxio/users/telegram/link` | Vincula la cuenta con `initData` de Telegram validado. |
| `/player/*` | Directorio, perfil, tarjetas, fotos, relaciones y bots. |
| `/match/matches/*` | Crear partido, convocar jugadores, grupos, balancear, votar resultado, reporte y tarjeta. |
| `/leagues/*` | Ligas propias/listado/detalle, altas, membresías, roles y pins. |
| `/webhooks/whatsapp` | Verificación y recepción firmada de Meta. |
| `/web/` y `/images/` | Archivos estáticos. |

Autenticación JWT y dependencias viven en `services/auth_service.py`. Antes de
agregar endpoints mutables, exigir la identidad y validar permisos de negocio.
Al revisar código existente, no asumir que todos los endpoints heredados ya lo
hacen: registrar una mejora de seguridad antes de cambiar su comportamiento.

## Frontend / Mini App

`src/web/index.html` carga Telegram WebApp SDK y los scripts:

- `app.js`: sesión, perfil, datos y UI principal.
- `match-creator.js`: creación de partidos, convocatoria y grupos.
- `finalize.js`: visualización final y ligas/rankings.
- `avatar-fix.js`: carga/ajuste de avatar.
- `enhancements.js` y `enhancements.css`: mejoras visuales.

El frontend usa rutas absolutas locales como `/web/...` y `/images/...` y asume
que API y web comparten origen. Si se despliega solo la UI en GitHub Pages o
Cloudflare Pages, agregar configuración explícita de URL de API y CORS; de lo
contrario las llamadas a la API fallarán.

## Integraciones

### Telegram

`bot/telegram_bot.py` crea el bot con polling, configura el botón de menú de
Mini App y ejecuta un worker de notificaciones. Los handlers se agrupan en
comandos, callbacks, conversaciones y mensajes en `telegram_handlers.py`.

El comando `/start` crea/consulta `TelegramIdentity`; si hay URL pública, ofrece
el botón de Mini App. La vinculación definitiva desde la web valida `initData`
con `telegram_webapp_service.py`.

### WhatsApp

`routers/whatsapp_router.py` valida la firma `x-hub-signature-256` de Meta y
deriva mensajes a `WhatsAppService`. Las conversaciones persistentes y estados
viven en `services/whatsapp_conversation_service.py` y los modelos de identidad/
sesión de WhatsApp.

## Pruebas: advertencia crítica

**Nunca ejecutar `pytest`, `start_test.py` o `src/run_test.py` contra una base
real o la URL normal de `.env`.**

`src/test/conftest.py` ejecuta `Base.metadata.drop_all()` al inicio/final de la
sesión y antes de cada prueba. Al no sobrescribir el motor, apunta a
`settings.DATABASE_URL` y elimina todas las tablas de esa base. Esto ya provocó
la pérdida del esquema local durante un diagnóstico.

Antes de volver a ejecutar integración:

1. Crear una base exclusiva, por ejemplo `maxiodb_test`.
2. Hacer que pytest construya un `DATABASE_URL` de test antes de importar
   `src.database`.
3. Añadir una guarda que rechace `drop_all()` si la URL no contiene una marca de
   test inequívoca.
4. Restaurar datos o esquema de desarrollo sólo desde un backup o con
   autorización explícita; crear tablas no recupera los datos anteriores.

`python -m compileall -q src` es una comprobación segura de sintaxis. La suite
recolecta 36 pruebas en el estado actual, pero no es segura hasta aislarla.

## Convenciones y riesgos técnicos conocidos

- Mantener la lógica de negocio en servicios y los routers delgados.
- `database.py` mezcla inicialización y migración manual; no introducir SQL
  destructivo ni supuestos sobre tablas/constraints sin revisar una instalación
  existente.
- Pydantic v2 emite avisos porque algunos schemas aún usan `class Config` con
  `orm_mode`; la alternativa moderna es `ConfigDict(from_attributes=True)`.
- FastAPI marca `@app.on_event("startup")` como deprecado; considerar `lifespan`
  al modernizar el arranque.
- Hay texto con codificación dañada (`Ã`, `ðŸ`) en varios módulos y manuales.
  Preservar UTF-8 al editar y corregirlo de manera controlada.
- `.env`, `.venv`, logs y artefactos de build no se versionan. Nunca incluir
  tokens, contraseñas, URLs internas o datos privados en commits o respuestas.
- Comprobar siempre `git diff --check`; actualmente puede advertir por CRLF.

## Forma recomendada de trabajar

1. Leer este archivo y luego inspeccionar sólo los archivos directamente
   relacionados con la solicitud.
2. Ejecutar `git status --short` y conservar los cambios ajenos.
3. Para una corrección, seguir la cadena `router -> service -> model/schema ->
   frontend o integración` según corresponda.
4. Añadir o actualizar una prueba únicamente cuando exista una base aislada.
5. Verificar primero con compilación y revisiones estáticas; no arrancar procesos
   externos ni tocar datos reales sin necesidad y autorización.

## Puntos de entrada rápidos

| Necesidad | Archivo inicial |
| --- | --- |
| Arranque/configuración | `src/main.py`, `src/config.py`, `src/database.py` |
| Autenticación y usuarios | `src/services/auth_service.py`, `src/routers/user_router.py` |
| Partidos/balanceo/resultados | `src/services/match_service.py`, `src/routers/match_router.py` |
| Jugadores/perfiles/tarjetas | `src/services/player_service.py`, `src/routers/player_router.py` |
| Ligas/rankings | `src/services/league_service.py`, `src/routers/league_router.py` |
| Mini App | `src/web/index.html`, `src/web/app.js`, `src/web/match-creator.js` |
| Telegram/túnel | `src/bot/telegram_bot.py`, `src/services/cloudflare_tunnel_service.py` |
| WhatsApp | `src/routers/whatsapp_router.py`, `src/services/whatsapp_service.py` |
