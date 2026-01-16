# src/utils/logger_config.py

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# =========================
# Base dir compatible EXE
# =========================
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        # Carpeta donde está el .exe
        return Path(sys.executable).resolve().parent
    # Raíz del proyecto (../../ desde utils)
    return Path(__file__).resolve().parents[2]

BASE_DIR = get_base_dir()

# =========================
# Logs directory
# =========================
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

app_log_path = LOG_DIR / "app.log"
test_log_path = LOG_DIR / "test.log"

# =========================
# Log format
# =========================
log_format = (
    "%(asctime)s [%(levelname)s] %(name)s "
    "(%(filename)s:%(funcName)s:%(lineno)d) "
    "[PID:%(process)d | %(threadName)s]: %(message)s"
)

# =========================
# App logger
# =========================
app_logger = logging.getLogger("maxio")
app_logger.setLevel(logging.INFO)

app_file_handler = RotatingFileHandler(
    app_log_path,
    maxBytes=5_000_000,
    backupCount=3,
    encoding="utf-8"
)
app_file_handler.setFormatter(logging.Formatter(log_format))

app_stream_handler = logging.StreamHandler()
app_stream_handler.setFormatter(logging.Formatter(log_format))

if not app_logger.handlers:
    app_logger.addHandler(app_file_handler)
    app_logger.addHandler(app_stream_handler)

# =========================
# Test logger
# =========================
test_logger = logging.getLogger("maxio.test")
test_logger.setLevel(logging.INFO)

test_file_handler = RotatingFileHandler(
    test_log_path,
    maxBytes=5_000_000,
    backupCount=3,
    encoding="utf-8"
)
test_file_handler.setFormatter(logging.Formatter(log_format))

if not test_logger.handlers:
    test_logger.addHandler(test_file_handler)
