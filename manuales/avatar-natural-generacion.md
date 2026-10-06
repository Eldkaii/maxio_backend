# Avatar natural: dirección y generación

La figura se integra con el barrio sin cambiar la paleta ni las paredes. Se conserva la foto personal y el logro de afinidad existente. El vestuario sigue siendo una vista previa local: este cambio visual no concede prendas ni añade persistencia.

Herramienta: imagegen integrada, sin CLI ni API externa. PNG con alpha preservado; originales previos conservados. Recursos finales: `src/images/player-avatar-natural-{base,bolso,manya,training}-v1.png`. Catálogo compartido en `src/web/barrio.js`.

## Prompts

### Base

Use case: stylized-concept.
Asset type: transparent full-body character for Max_io, an amateur football player profile standing in a realistic Montevideo courtyard at dusk.
Primary request: replace a faceless black superhero mannequin with a grounded, relatable amateur footballer. Create ONE adult man, late twenties, ordinary lean-average build, natural human proportions, short slightly messy dark hair, understated friendly facial features, natural skin, relaxed neutral standing posture, arms hanging slightly clear of the torso, hands relaxed, feet on the same ground plane. Nothing exaggerated.
Style: restrained naturalistic digital illustration, almost photographic material rendering, very subtle painted texture, no cartoon outlines, no glossy videogame/plastic surface, no heroic bodybuilding or perfect model styling. Clothing is the focus.
Outfit: simple washed charcoal-navy loose training T-shirt, dark navy football shorts above knee, muted off-white football socks to mid calf, worn black leather turf football shoes with small off-white details. Cloth seams, subtle wrinkles and soft realistic drape. No logos, text, crest, cap or ball in the base outfit.
Lighting: soft cool blue evening ambient with subdued warm streetlamp illumination from upper right, readable front, no neon glow or aura. Intended to sit naturally on concrete in a dark brick courtyard.
Composition: portrait 2:3, front view with slight natural asymmetry, full body from hair to both soles, figure centered, fills 90 percent of canvas height, safe padding at all sides. Normal 7.5-head-tall adult proportions. Consistent neutral pose suitable for changing jerseys, shorts, boots and caps later.
Output: genuinely transparent PNG alpha background, clean natural cutout edges. NO courtyard, floor plane, backdrop, painted checkerboard, frame, captions, decorative light or cast shadow outside silhouette.

Tras generar la base se pidió un recorte transparente sin halo, conservando identidad, ropa, postura y encuadre.

### bolso

undefined

### manya

undefined

### training

undefined

## Release

`releaser.py` ya incluye `src/images/` y `src/web/`. No se genera commit ni ejecutable en esta intervención; se conserva VERSION 2.5.1 y corresponde incrementarla al preparar un commit distribuible con estos cambios.
