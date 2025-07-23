# start.py

import sys
import os

# Asegura que el directorio src esté en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import main  # Asegúrate de que src/main.py tenga un método main()

if __name__ == "__main__":
    main()
