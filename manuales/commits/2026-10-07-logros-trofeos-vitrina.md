# Logros administrables y trofeos en Vitrina

- Administración: creación y edición de condiciones, tipo Logro/Trofeo y selector visual de premios individuales.
- Persistencia de premios obtenidos, fecha de asignación y metadatos del perfil (imagen, tipo, condiciones y familia).
- Vitrina: cinco posiciones de copas en orden 2 → 1 → 3 → 4 → 5, tamaño, capas y superposición ajustados; anclaje al final del username. Placa compacta sin logros ni contador de trofeos.
- Cada copa abre la colección completa inferior, con fecha y requisitos. Los premios sin fecha histórica muestran que no está registrada.
- Se incluyen las imágenes originales y los 23 PNG procesados, las novedades móviles del encabezado y el refresco de métricas administrativas pendientes de commit.
- Compatibilidad de base: tablas de definiciones/asignaciones y columna `reward_type` añadida de forma idempotente al iniciar. No se ejecutaron migraciones ni pruebas destructivas sobre la base real para este commit.

## Release

Versión 2.5.1 → 2.6.0 por nuevas funciones distribuibles y recursos. `releaser.py` ya incluye `src/web` y `src/images` completos; no requiere nuevas dependencias ni rutas de empaquetado. No se generó ejecutable ni se distribuyó `.env`.

## Verificación

- Compilación Python de archivos modificados y comprobación de sintaxis JavaScript.
- Verificación de interfaz con datos ficticios: Vitrina, copas, perfil vacío, nombres largos e inyección; anchos de 320, 390 y 1440 px según escenario.
- Comprobación de metadatos de premios en la serialización del perfil realizada durante la corrección.
- `git diff --check`.

## Pendientes conocidos

- La prioridad de 1 a 100 y el desempate por fecha aún no están implementados; las posiciones se llenan con el orden actual de los premios recibidos.
- La evaluación de premios se realiza al consultar el perfil, no mediante un barrido global al crear una definición.
- No se reconstruye la fecha histórica de cumplimiento de un premio anterior a su primera evaluación.
- El tiempo acumulado de las interacciones anteriores no tiene una medición verificable en el contexto disponible; no se asignó una duración estimada al registro externo.
