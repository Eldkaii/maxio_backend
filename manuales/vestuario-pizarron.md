# Pizarrón del perfil

## Miniapp (hasta 760 px)

Composición horizontal 3:2 independiente en `src/images/locker-mobile-landscape-v2.png`,
seleccionada con `picture`. Muestra una persona de pie, pizarrón y un único casillero.
No hay desplazamiento horizontal; camiseta y texto usan coordenadas de la imagen
1536 × 1024. Las demás prendas siguen disponibles en el inventario.

Generada con la herramienta integrada de imagen usando el vestuario como referencia.
Prompt: escena horizontal fotorealista 1536 × 1024 de club humilde; pizarrón vacío
grande en la mitad izquierda, un casillero vacío a la derecha con barra y banco;
persona con capucha de pie en el borde derecho mirando al casillero, rostro invisible,
encuadrada hasta los muslos. Poco piso y techo, pintura gastada, luz cálida, sin texto
ni ropa incorporada al fondo. Escritorio conserva su imagen y coordenadas anteriores.

## Escritorio

Se conserva la fotografía aportada en `src/images/locker-chalkboard-reference-v8.jpg`.
Sólo el interior de la pizarra se cubre con un recorte SVG del recurso
`src/images/locker-chalkboard-v8.png`; marco, vestuario y persona mantienen la foto original.
Los datos reales se dibujan como texto SVG escapado en `locker-room.js`, con coordenadas
proporcionales a la escena. El username permanece en la camiseta.

Recurso limpio generado con la herramienta integrada de imagen (sin CLI).
Prompt: “Precise object edit. Use this exact photograph unchanged, including framing,
wall, three locker bays, rails, man, ball, floor and lighting. ONLY erase ALL the tiny
white writing from the inside of the black chalkboard at left. Leave its wooden frame
and tray absolutely unchanged. Replace writing with realistically wiped dark charcoal
slate with very faint chalk dust, empty and ready to write new dynamic player stats
on top in a website. NO text, numbers, diagrams or UI added. Do not move or resize the
board. Preserve everything outside its inner slate. Same 3:2 aspect ratio.”

Verificación: sintaxis JavaScript y `git diff --check`. Revisión visual en navegador pendiente.
