# Miniapp: Vitrina, Cantina, Vestuario y Barrio

La entrada autenticada `/web/` usa `club-app.js` y `club-app.css`.
La navegación inferior mantiene una sola pantalla visible y abre Vitrina al ingresar.
El perfil público continúa con su presentación anterior.

- **Vitrina:** username, nombre, nacionalidad, ELO, resumen de resultados, cinco
  habilidades, últimos encuentros y logros. La estantería muestra medallas para
  participación, copas para victorias y trofeos para relaciones. Son representaciones
  de los hitos existentes de `career.milestones`, sin nuevas reglas de desbloqueo.
- **Vestuario:** abre el creador existente y permite recorrer todos los partidos,
  consultar equipos y votar resultados pendientes. Incluye acceso a ligas y rankings.
- **Cantina:** búsqueda de jugadores, dupla y rivalidad destacadas e historial paginado
  de conexiones humanas, con partidos juntos y enfrentados.

Paleta de revoque crema, madera oscura, verde apagado y bronce. La foto del vestuario
aparece como apoyo visual en la convocatoria; los datos principales son HTML legible.
Se conserva el DOM heredado oculto que necesitan los flujos de sesión y creación.

Vitrina usa información en mayúsculas, ficha con pared texturada y cinco tarjetas
de habilidades (dos columnas en celular; cinco en pantallas anchas), con cifras
grandes y barras accesibles. Las texturas reutilizan el fondo limpio existente y
capas CSS suaves de veta, sin nuevos recursos ni cambios de datos.
No se duplican IDs ni se eliminan sus manejadores de eventos.

## Historiales

Dos endpoints nuevos, autenticados y de sólo lectura:

- `GET /player/me/matches?offset=0&limit=20`
- `GET /player/me/connections?offset=0&limit=20`

Devuelven `items`, `has_more` y `next_offset`. El límite máximo es 50.
La identidad se toma de la sesión, nunca de un username enviado por el navegador.
La serialización de partidos se comparte con el perfil en `club_history_service.py`.
La consulta de partidos ordena por fecha e ID y pagina en SQL.
No requiere cambios de esquema. Reiniciar el backend para cargar las rutas nuevas.

## Validación

- `node checks/verify-club.cjs`: servidor local de fixtures, sin aplicación ni BD.
  Ocho casos: 320, 390 y 1440 px, las tres pantallas, nombres largos, texto malicioso
  y jugador sin logros. Comprueba navegación, detalle, dos páginas de historial,
  creador de partidos, conexiones y refresco sin duplicados.
- `python checks/test_club_history.py`: cuatro pruebas de serialización aislada
  por AST, sin importar configuración ni inicializar base de datos.
- Compilación de Python, sintaxis JavaScript y `git diff --check`.

Capturas de revisión en `tools/ui-review/club/` (no distribuir fixtures como datos reales).
La integración con PostgreSQL real y Telegram no se ejecutó durante esta revisión.

No se creó commit ni ejecutable. Este cambio afecta comportamiento distribuible;
corresponde revisar/incrementar la versión de `releaser.py` al preparar su commit de release.
