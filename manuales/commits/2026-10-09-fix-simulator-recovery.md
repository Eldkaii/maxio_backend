# Recuperación de membresía pendiente del simulador

Commit: `28cbb7a` — `feat(admin): add control center and safe simulator recovery`

## Diagnóstico

El primer fallo conservado ocurrió el 2026-10-08 a las 18:23:54, en una adhesión
a la liga 5. Los arranques posteriores encontraban el mismo diario sin respuesta.
Una consulta GET a la API local confirmó que la membresía ya existía, mientras
el estado del simulador no la tenía registrada. El código anterior descartaba
la excepción original: no permite atribuir el incidente a un timeout o un HTTP
500 concreto. Otros errores de logs rotados no se atribuyen a este incidente.

## Corrección

- Reconciliación de adhesiones inciertas por GET: exige coincidencia de trabajo,
  paso, endpoint, liga e ID de jugador. Sólo una membresía confirmada habilita
  continuar. Una ausencia no habilita reenviar una escritura incierta.
- Reanudación de ese paso sin POST y sin duplicar membresías locales.
- `--recover` con bloqueo exclusivo y respaldo local para confirmar la respuesta
  sin iniciar nuevas acciones del simulador.
- Registro seguro del tipo de excepción y código HTTP en nuevas interrupciones.
- Creación de ligas con `start_date` y `end_date`, requeridos por el contrato
  actual; antes el simulador enviaba sólo nombre y visibilidad.

## Validación

Pruebas standalone con API falsa, reloj y temporales, sin pytest ni base de datos:
recuperación confirmada, lectura negativa/malformada/fallida, segundo reinicio,
no repetición de POST, respaldo, diagnóstico sin cuerpo privado y fechas de liga.
Se conserva la simulación de 60 días y sus reglas deportivas.

La recuperación local se ejecutó con `--recover`: API confirmó la membresía,
se creó un respaldo junto al estado y `--status` pasó a informar
`Escritura por resolver: False`. No se hicieron POST, cambios SQL ni se reinició
la aplicación durante la reparación; el worker retomará al reiniciar normalmente.

## Release

Se mantiene la versión 2.8.0 preparada con el rediseño administrativo aún sin
commit: ambos cambios integran el mismo próximo release. El empaquetado ya
incluye los submódulos de `extensions.activity_simulator`. Sin cambios de esquema,
dependencias nuevas ni ejecutable generado.
