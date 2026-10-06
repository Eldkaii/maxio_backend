# Avatar, vestuario y barrio

El avatar es la identidad visual principal del jugador. Se presenta de cuerpo
completo en la cabecera, con proporciones humanas, ropa deportiva de caída natural
y luz ambiente compatible con el patio. La paleta de la interfaz y los muros se
conservan; el personaje no lleva halo neón ni cuerpo de maniquí.
Las estadísticas acompañan esa identidad, sin ocupar el lugar del personaje.

## Implementado en la presentación

- Avatar protagonista en escritorio y móvil, con acceso al vestuario.
- Catálogo visual de entrenamiento, remera Bolso, remera Manya y gorra con botines.
  Todas las apariencias conservan la misma persona, encuadre y postura. Probar una apariencia actualiza
  el personaje de la cabecera. Es una vista previa local, sin guardado ni inventario.
- Progreso del logro existente: diez partidos para elegir afinidad de cuadro.
  La disponibilidad y la elección provienen de `achievements` en la API.
- Adelanto conceptual de tres muros alrededor del avatar; la pintada central
  refleja la afinidad existente. No representa un barrio guardado o editable.
- Presentación de las próximas funciones de vestuario y barrio.

## Dirección acordada para las próximas funciones

- Vestimenta y accesorios desbloqueables mediante logros y rachas de partidos.
  Mostrar qué se puede conseguir, cuánto falta y qué se obtuvo al terminar de jugar.
- Barrio formado por un conjunto de muros, como escenario persistente del avatar.
- Pintadas estilo grafiti del cuadro del propietario.
- Pintadas de amigos o rivales con quienes se compartieron varios partidos.
  Las relaciones de cancha son parte del valor del barrio.

## Trabajo pendiente de producto y backend

La representación natural actual es una base visual común, no un retrato del
usuario ni un creador de personajes. La foto personal sigue siendo independiente.
Los PNG son conjuntos completos de vista previa: todavía no se combinan prendas
por separado. Para incorporar un inventario modular, cada capa de remera, short,
calzado y gorra debe usar un mismo encuadre, pose, iluminación y puntos de anclaje.
No regenerar una persona distinta para cada prenda.

Definir catálogo, umbrales y significado de las rachas (victorias, participación
u otra regla) antes de conceder recompensas. Los desbloqueos deben calcularse
en servicios y validarse en servidor; una vista previa no concede propiedad.

Guardar el equipamiento elegido y el barrio por jugador. Definir cuántos partidos
habilitan una pintada, los permisos sobre cada muro y cómo el propietario acepta,
oculta o reemplaza contribuciones. La vista pública debe usar ese estado guardado.
No se crearon migraciones, inventarios ni endpoints mutables para este adelanto.

## Verificación y release

Verificación de JavaScript y renderizado con datos ficticios en Chrome, sin usar
la base de datos. El personaje natural usa PNG con transparencia en `src/images/`;
el patio conserva sus imágenes y coordenadas de muros existentes.
Los cambios de `src/web/` están dentro del bundle existente de `releaser.py`.
No se genera un commit ni release; revisar e incrementar VERSION al prepararlos.
