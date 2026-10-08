# Ligas, Cantina, perfiles y evaluaciones

Mensaje: `feat: improve leagues, club profiles and player evaluations`
Commit: el que incorpora este archivo (consultar `git log -1 --format=%h -- manuales/commits/2026-10-08-feat-ligas-cantina-evaluaciones.md`).

## Cambios

- Calendario obligatorio de ligas, validación de inicio/fin, cierre de inscripciones y límites temporales para partidos y puntos. Migración aditiva e idempotente para ligas existentes.
- Tarjetas de ligas con rankings, detalle expandido, búsqueda, recomendaciones, creación e inscripción; distinción pública/privada y confirmación al unirse.
- Cantina con evaluaciones pendientes destacadas, tres conexiones principales e historial.
- Perfiles ajenos mediante la Vitrina de la Mini App, aviso de evaluaciones recibidas y enlace para volver al perfil propio.
- Formulario de evaluación con habilidades actuales, barras, selección de atributos, validación, confirmación y actualización de pendientes.
- Se conserva el ID de cada destinatario en el contrato de evaluaciones; compatibilidad por nombre para respuestas anteriores que omitían el ID.

## Verificación

- Sintaxis JavaScript de app.js, club-app.js y player.js; compilación Python de src.
- Serialización de EvaluationInfo: ID y nombre del destinatario preservados.
- Verificación del formulario en Chrome con datos sintéticos a 320, 390 y 1440 px: apertura, selección, payload de envío, confirmación, cierre y eliminación del pendiente; respuestas con y sin ID.
- Revisión visual móvil y `git diff --check`.
- No se ejecutó pytest, ni integración contra PostgreSQL real, ni migraciones sobre datos reales.

## Release

Versión 2.6.0 → 2.7.0 por nuevas funciones distribuibles. El empaquetado incluye src/web completo, incluido club-evaluation.css; no necesita nuevas dependencias. No se construyó un ejecutable.

## Pendientes conocidos

- El endpoint heredado de actualización de estadísticas recibe evaluator_username y necesita reforzar autenticación y validación del permiso en servidor; la comprobación del formulario no sustituye esa protección.
- El perfil público todavía conserva código antiguo en player.js antes de redirigir. El resumen de ligas se omite en Vitrina pública para no mostrar las ligas de la sesión visitante.
- La migración asigna a ligas sin fechas un calendario anual desde su ejecución; no reconstruye fechas históricas de creación.
- La validación del formulario usa un servidor de prueba con datos ficticios, no comprueba una escritura real en PostgreSQL.

## Tiempo

Registro externo solicitado en la entrada Max_io de ../la_gerencia/datos.json. Duración pendiente de confirmación del usuario: el historial disponible no permite medir el acumulado con fiabilidad.
