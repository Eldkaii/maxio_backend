# Equipos completados con bots

## Commit

- Hash: consultar `git log --oneline -1` en la rama que contiene este archivo.
- Mensaje: `feat(matches): fill teams with bots after real-player balance`

## Objetivo

Permitir que quien crea un partido elija el tama\u00f1o de cada equipo y completar
los lugares restantes con bots sin que sus estad\u00edsticas alteren el balance de
los jugadores reales.

## Incluido

- Selecci\u00f3n de dos a diez jugadores por equipo en Telegram y WhatsApp.
- Balanceo de jugadores reales con cantidades impares permitidas.
- Incorporaci\u00f3n posterior de bots hasta completar cada equipo.
- Diferencia de un bot entre equipos cuando la cantidad de humanos es impar.
- Exclusi\u00f3n de bots del conteo de votos requerido para cerrar un partido.
- Prueba de siete humanos en equipos de cinco: cuatro humanos y un bot contra
  tres humanos y dos bots.

## Listo y verificado

- La prueba espec\u00edfica de relleno con bots pasa.
- La suite de conexi\u00f3n de WhatsApp pasa: 12 pruebas.
- Git no detecta errores de espacios en blanco.

## Consideraciones

- Se requieren suficientes jugadores bot disponibles para completar el tama\u00f1o
  elegido; de lo contrario, la creaci\u00f3n del partido informa el error.
- Los bots contin\u00faan siendo jugadores de sistema sin usuario, Telegram ni
  WhatsApp asociados.
