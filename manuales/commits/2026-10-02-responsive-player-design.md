# Rediseño visual del perfil y Mini App

## Cambios

- Paleta verde oscuro, acentos suaves, tipografía y espaciado unificados.
- Perfil con identidad, foto editable, ELO, logros, partidos, victorias,
  empates, porcentaje de victorias y últimos cinco resultados visibles.
- Seis tarjetas de rendimiento, selector manual de habilidades/avatar y
  personalización existente conservada. Se elimina la rotación automática.
- Escritorio con columnas; móvil con flujo vertical, tarjetas en dos columnas
  y barra inferior de acciones. Se elimina el lienzo fijo con `zoom`.
- Ligas, partidos, evaluaciones y conexiones con superficies coherentes.
- Perfil público y diálogos integrados al mismo estilo; identidad pública
  renderizada con los datos del perfil para evitar depender de una petición paralela.
- Controles de liga accesibles por teclado, foco visible y movimiento reducido.
- Se conserva el contenedor del selector al refrescar los datos del perfil.

`responsive.css` reemplaza la capa visual del dashboard. `redesign.css` se
conserva en disco, pero el inicio ya no lo carga: sus múltiples composiciones
anteriores no compiten con el nuevo diseño. Se preservan los cambios previos
de backend, imágenes y otros flujos presentes en el árbol de trabajo.

## Verificación

- Chrome headless con API ficticia local; ninguna conexión a PostgreSQL.
- Anchos efectivos de 320, 390, 768 y 1440 px, sin desborde horizontal.
- Perfil poblado/vacío, nombre largo, habilidades/avatar, recarga del perfil,
  conexiones, acceso, búsqueda, creación de partido/liga y editor de perfil.
- Perfil público en móvil y escritorio. Activación por teclado de ligas,
  plegado de partidos y conexiones.
- `node --check` para los scripts modificados y `git diff --check`.
- Capturas locales en `tools/ui-review/`, con datos exclusivamente ficticios.
  El comprobador local `tools/verify-responsive.cjs` está bajo la carpeta
  ignorada `tools/`; no forma parte del bundle.
- No se ejecutó pytest, no se inició el backend y no se probaron escrituras
  reales ni el cliente nativo de Telegram. La validación de Mini App cubre
  distribución WebView y áreas seguras mediante CSS.

## Release

Hay impacto distribuible en `src/web/`, carpeta ya incluida por `releaser.py`.
No se genera ejecutable ni commit en esta tarea; se mantiene `VERSION` 2.5.1.
Actualizar la versión al preparar el commit/release que incorpore el rediseño.
