# src/utils/logger_config.py

import logging
import os

# Ruta base del proyecto (la raíz que contiene src/, logs/, etc.)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Crear carpeta de logs en la raíz del proyecto
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Archivos de log
app_log_path = os.path.join(LOG_DIR, "app.log")
test_log_path = os.path.join(LOG_DIR, "test.log")

# Logger general
app_logger = logging.getLogger("maxio")
app_logger.setLevel(logging.INFO)

app_file_handler = logging.FileHandler(app_log_path, encoding="utf-8")
app_file_handler.setLevel(logging.INFO)
app_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

app_stream_handler = logging.StreamHandler()
app_stream_handler.setLevel(logging.INFO)
app_stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

app_logger.addHandler(app_file_handler)
app_logger.addHandler(app_stream_handler)

# Logger para tests
test_logger = logging.getLogger("maxio.test")
test_logger.setLevel(logging.INFO)

test_file_handler = logging.FileHandler(test_log_path, encoding="utf-8")
test_file_handler.setLevel(logging.INFO)
test_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

test_logger.addHandler(test_file_handler)
