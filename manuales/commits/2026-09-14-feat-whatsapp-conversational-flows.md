# Flujos conversacionales de WhatsApp

## Commit

- Hash: consultar `git log --oneline -1` en la rama que contiene este archivo.
- Mensaje: `feat(whatsapp): add conversational player and match flows`

## Objetivo

Extender la integración de WhatsApp para conservar la identidad y el estado de conversación, y habilitar desde WhatsApp los flujos de jugadores, partidos y evaluaciones.

## Incluido

- Modelos y servicios para identidad y sesión de WhatsApp.
- Orquestación conversacional de consultas de jugadores, creación de partidos y evaluaciones.
- Soporte para botones, listas, imágenes y descarga de archivos multimedia mediante WhatsApp Cloud API.
- Pruebas aisladas para el webhook, mensajes interactivos, parseo de datos y normalización de usernames.
- Inicio y detención automáticos de un túnel Cloudflare en entorno de prueba, con documentación de uso.
- Inicio del worker de notificaciones de Telegram mediante `post_init`, cuando el loop asíncrono ya está disponible.
- Normalización a minúsculas de los usernames ingresados en Telegram y en flujos relacionados.

## Listo y verificado

- Los flujos conversacionales y los componentes de transporte cuentan con pruebas unitarias aisladas.
- Los cambios no introducen errores de espacios en blanco detectados por Git.

## Temporal / configuración externa

- El túnel rápido de Cloudflare se usa únicamente cuando `APP_ENV=TEST` y su URL cambia en cada ejecución.
- WhatsApp sigue requiriendo las credenciales de Cloud API y la configuración del webhook en Meta.

## Pendiente antes de producción

- Usar un túnel o dominio HTTPS permanente.
- Completar pruebas de integración con Meta y Telegram en un entorno controlado.
- Definir retención y limpieza de sesiones conversacionales antiguas.
