# Fondo panorámico de la Mini App

La imagen aportada por el usuario se conserva sin modificar en
`src/images/club-panorama-v2.png`.

- Cantina / conexiones: encuadre izquierdo y primer botón.
- Vitrina / información del jugador: encuadre central y segundo botón.
- Vestuario / creación de partidos: encuadre derecho y tercer botón.

`club-app.js` actualiza `data-club-room` en el dashboard. Una única capa fija
en `club-app.css` usa `background-size: auto 100%`, conservando la relación de
aspecto original. Cada posición navega al tercio correspondiente sin estirar
la fotografía. El cambio de posición dura 700 ms; los dispositivos con movimiento reducido
desactivan la transición. Los paneles tienen fondos translúcidos para conservar
legibilidad.

Se retiró la regla de fondo exclusiva de Vitrina que sobrescribía la imagen
compartida. La anterior pared generada ya no es el fondo de esa pantalla.

Verificación: `node --check src/web/club-app.js`, `git diff --check` y
`node checks/verify-club.cjs vitrina,vestuario,cantina`. Cinco vistas de Chrome
con datos sintéticos, anchos de 320, 390 y 1440 px, sin errores ni desbordes.
No se inició el backend ni se accedió a la base real. No se preparó un commit
o release; al distribuir, incluir la nueva imagen entre los recursos.
