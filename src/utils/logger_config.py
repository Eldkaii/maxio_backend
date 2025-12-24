# src/utils/logger_config.py

import logging
import os
from logging.handlers import RotatingFileHandler

# Ruta base del proyecto (la raíz que contiene src/, logs/, etc.)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Crear carpeta de logs en la raíz del proyecto
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Archivos de log
app_log_path = os.path.join(LOG_DIR, "app.log")
test_log_path = os.path.join(LOG_DIR, "test.log")

# Nuevo formato con archivo, función, línea, proceso e hilo
log_format = (
    "%(asctime)s [%(levelname)s] %(name)s "
    "(%(filename)s:%(funcName)s:%(lineno)d) "
    "[PID:%(process)d | %(threadName)s]: %(message)s"
)

# Logger general
app_logger = logging.getLogger("maxio")
app_logger.setLevel(logging.INFO)

# Handler de archivo rotativo
app_file_handler = RotatingFileHandler(
    app_log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
)
app_file_handler.setLevel(logging.INFO)
app_file_handler.setFormatter(logging.Formatter(log_format))

# Handler para consola (Stream)
app_stream_handler = logging.StreamHandler()
app_stream_handler.setLevel(logging.INFO)
app_stream_handler.setFormatter(logging.Formatter(log_format))

# Evitar duplicar bot_handlers
if not app_logger.handlers:
    app_logger.addHandler(app_file_handler)
    app_logger.addHandler(app_stream_handler)

# Logger para tests
test_logger = logging.getLogger("maxio.test")
test_logger.setLevel(logging.INFO)

test_file_handler = RotatingFileHandler(
    test_log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
)
test_file_handler.setLevel(logging.INFO)
test_file_handler.setFormatter(logging.Formatter(log_format))

if not test_logger.handlers:
    test_logger.addHandler(test_file_handler)
