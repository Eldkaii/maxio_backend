# Registro de commit: simulador y consola administrativa

- Se consolidan el simulador opcional de actividad, su límite individual de
  partidos, el log rotativo y la consulta protegida desde Administración.
- Se incluyen las mejoras de interfaz, ligas, vestuario, perfil y recursos
  estáticos que permanecían pendientes en el árbol de trabajo.
- Revisión de release: el cambio modifica comportamiento distribuible y el
  punto de entrada, pero no agrega dependencias ni cambia entradas de
  `releaser.py`; se conserva la versión actual. La extensión sigue siendo
  opcional y externa a `src/`.
- Verificación: `checks/test_activity_simulator.py`,
  `checks/test_simulator_log.py`, comprobación visual `checks/verify-admin-log.cjs`,
  compilación Python/JavaScript y `git diff --check`.
