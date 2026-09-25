# Administración, acciones flotantes y creación de ligas

## Commit

- Hash: consultar `git log --oneline -1` en la rama que contiene este archivo.
- Mensaje: `feat(miniapp): add admin console and league member creation`

## Incluido

- Cuenta administradora global sin perfil de jugador, con consola propia,
  métricas operativas y alta protegida de jugadores reales.
- Redirección de administración separada de la Mini App de jugadores.
- Mejora del perfil móvil: cierre de sesión confirmado y menú flotante radial
  para crear partidos, ligas y buscar jugadores; la creación de partidos tiene
  la prioridad visual principal.
- Selección de jugadores al crear una liga. La API valida e incorpora los
  miembros iniciales en la misma transacción que crea la liga y la Mini App
  cierra el diálogo al completarse.
- Datos semilla con nombre y apellido opcionales, aplicados al crear usuarios.

## Release

- Versión actualizada de `2.3.0` a `2.4.0`: cambia comportamiento distribuible
  de la API y recursos estáticos empaquetados.
- `releaser.py` ya incluye `src/web/`, imágenes y fuentes; no requirió cambios
  adicionales de empaquetado.
- No se generó un ejecutable en esta sesión. El release real debe comprobar los
  recursos incluidos y no distribuir el `.env` copiado por el script actual.

## Verificación

- `.venv\\Scripts\\python.exe -m compileall -q src`
- Validación del contrato `LeagueCreate` con miembros iniciales.
- `git diff --check` sin errores de formato; Git puede advertir conversiones
  CRLF configuradas en el árbol de trabajo.
- No se ejecutó `pytest`: la suite actual puede ejecutar `drop_all()` contra la
  base indicada por `.env`.
