# src/run_tests.py

import sys
import pytest
import os
from src.utils.logger_config import test_logger as logger

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def run_tests(test_paths=None, verbose=False, show_warnings=False):
    """
    Ejecuta tests usando pytest.

    Args:
        test_paths (list[str] or None): Lista de archivos o carpetas de tests a ejecutar.
                                        Si es None, ejecuta todos los tests bajo 'test/'.
        verbose (bool): Muestra detalles de cada test.
        show_warnings (bool): Muestra warnings durante la ejecución (por defecto ocultos).
    """
    if test_paths is None:
        test_paths = ["test/"]  # default: correr todos los tests bajo test/

    logger.info(f"🚀 Iniciando ejecución de tests en: {test_paths}")

    args = test_paths.copy()
    if verbose:
        args += ["-v", "--capture=no"]  # ver output en tiempo real

    # Control de warnings
    if not show_warnings:
        args += ["-p", "no:warnings"]  # oculta warnings

    # Activa logging en consola (INFO+)
    args += ["--log-cli-level=INFO"]

    exit_code = pytest.main(args)

    if exit_code == 0:
        print("\n\033[92m🎉 TODOS LOS TESTS PASARON CORRECTAMENTE 🎉\033[0m\n")
    else:
        print(f"\n\033[91m❌ Algunos tests fallaron. Código de salida: {exit_code} ❌\033[0m\n")

    return exit_code


if __name__ == "__main__":
    print("sys.argv:", sys.argv)

    # Podés pasar tests, además flags --verbose o --show-warnings
    tests_to_run = []
    verbose = False
    show_warnings = False

    for arg in sys.argv[1:]:
        if arg in ("--verbose", "-v"):
            verbose = True
        elif arg == "--show-warnings":
            show_warnings = True
        else:
            tests_to_run.append(arg)

    if not tests_to_run:
        tests_to_run = None

    run_tests(tests_to_run, verbose=verbose, show_warnings=show_warnings)
