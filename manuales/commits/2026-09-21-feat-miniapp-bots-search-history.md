# Bots diseñables, búsqueda y renovación de la Mini App

## Commit

- Hash: consultar `git log --oneline -1` en la rama que contiene este archivo.
- Mensaje: `feat(miniapp): add custom bots and refresh player experience`

## Objetivo

Permitir diseñar bots al crear un partido y renovar los principales recorridos de la
Mini App: descubrimiento de jugadores, historial, ligas y últimos partidos.

## Incluido

- Diseñador de bots con barras deslizables para Tiro, Ritmo, Físico, Defensa y Aura.
- Aura visual de 0 a 100 con límite efectivo de 10 para bots, validado también en el backend.
- Nombre aleatorio compuesto con nombre y apellido de filas distintas de `bots_name`.
- Alta automática del bot al crear el partido e incorporación al balance y a los equipos.
- Arrastre táctil de jugadores y bots sobre la cancha, con vista previa de movimiento y sin abrir el menú nativo de Telegram.
- Búsqueda de jugadores reales por username, nombre o apellido desde el encabezado, con acceso a su perfil.
- Nuevo bloque visual de `Ranking en Liga` para Solo/Duo y Equipo.
- Rediseño del historial, sus relaciones y de Últimos partidos, incluyendo la tarjeta expandida con equipos azul/rojo separados por un rayo diagonal alineado.
- Nuevo recurso gráfico para el acceso a Tu historial y actualización del logotipo principal.

## Listo y verificado

- `python -m compileall -q src` ejecutado correctamente durante el desarrollo.
- `git diff --check` sin errores.

## Consideraciones

- Los puestos de ranking son visuales por ahora; no existe aún el sistema de clasificación.
- La validación visual final corresponde a la Mini App de Telegram, especialmente en pantallas pequeñas.
