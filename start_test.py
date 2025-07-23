# start.py

import sys
import os

# Asegura que el directorio src esté en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.run_test import run_tests

if __name__ == "__main__":
    run_tests()
