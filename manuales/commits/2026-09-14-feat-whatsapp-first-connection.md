# Primera conexión con WhatsApp Cloud API

## Commit

- Hash: consultar `git log --oneline -1` en la rama que contiene este archivo.
- Mensaje: `feat(whatsapp): establish first cloud api connection`

## Objetivo

Conectar Max_io a WhatsApp Business Platform Cloud API para recibir mensajes de texto mediante webhook y responder un texto básico.

## Incluido

- Variables de configuración de WhatsApp en `src/config.py`.
- Endpoint `GET` y `POST` en `/webhooks/whatsapp`.
- Verificación del challenge de Meta mediante `WHATSAPP_WEBHOOK_VERIFY_TOKEN`.
- Verificación de firma `X-Hub-Signature-256` mediante `META_APP_SECRET`.
- Cliente de salida para enviar texto con WhatsApp Cloud API.
- Respuestas iniciales para `hola`, `ayuda` y mensajes desconocidos.
- Registro del router dentro de FastAPI.
- Cliente HTTP configurado con `trust_env=False` para ignorar el proxy local inválido.
- Corrección de la ruta de `.env`, que ahora es estable aunque `run_test.py` cambie el directorio de trabajo.

## Listo y verificado

- Meta acepta el token, el WABA y el `Phone Number ID` configurados.
- La app de Max_io quedó suscrita al WABA para recibir eventos.
- El túnel público llegó al webhook y recibió HTTP 200.
- La firma del webhook fue validada localmente.
- Un mensaje de prueba se envió correctamente desde Max_io al número que inició la conversación.

## Temporal / solo para pruebas

- Se usa un número de prueba de WhatsApp.
- Se usa una URL temporal `trycloudflare.com`; cambia cada vez que se crea un túnel nuevo.
- El token de desarrollo de Meta puede expirar y debe renovarse en el panel de WhatsApp API Setup.
- Las respuestas son texto fijo y solo cubren mensajes entrantes de tipo `text`.
- La versión de Graph API tiene un valor por defecto y debe mantenerse actualizada mediante `WHATSAPP_GRAPH_API_VERSION`.

## Pendiente antes de producción

- Reemplazar el túnel por un dominio HTTPS permanente.
- Usar un token de system user con permisos y rotación definidos.
- Persistir identidad y estado de conversación de WhatsApp en la base de datos.
- Implementar idempotencia por `wamid`, cola/reintentos y trazabilidad de entregas.
- Implementar plantillas aprobadas para mensajes iniciados por Max_io fuera de la ventana de conversación.
- Conectar comandos de WhatsApp con los servicios de jugadores, partidos y evaluaciones existentes.
