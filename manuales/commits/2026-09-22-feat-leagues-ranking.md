# Sistema de ligas y ranking en la Mini App

## Commit

- Hash: consultar `git log --oneline -1` en la rama que contiene este archivo.
- Mensaje: `feat(leagues): add league management and mini app rankings`

## Objetivo

Incorporar ligas con membresías, administración, modalidades Solo/Duo y Grupos,
y una visualización de ranking dentro de la Mini App.

## Incluido

- Modelos, migración automática y API para ligas, miembros, administradores,
  ligas públicas/privadas y ligas nacionales obligatorias.
- Límite de tres ligas creadas por jugador no administrador.
- Ligas nacionales de Uruguay para ambas modalidades, identificadas como
  `UY 🇺🇾` y con adhesión automática de jugadores uruguayos.
- Validación de partidos de liga: participación humana mínima y bots permitidos
  como complemento.
- Puntos, victorias, derrotas y posición por integrante para presentar el
  ranking de cada liga.
- Ranking de Mini App separado en Solo/Duo y Grupos, con expansión sincronizada,
  detalle de clasificación y una liga destacada independiente por modalidad.
- Creación de ligas desde el encabezado de la Mini App.

## Listo y verificado

- `python -m compileall -q src` ejecutado correctamente.
- Inicialización de base de datos ejecutada para normalizar las ligas nacionales.
- `git diff --check` sin errores de formato.

## Pendiente

- Conectar la asignación efectiva de puntos al cierre de los partidos de liga.
- Completar pruebas de integración contra una base de datos aislada antes de
  liberar a producción.
