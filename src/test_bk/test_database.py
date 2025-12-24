# src/test/test_database.py

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
from src.database import SessionLocal
from src.utils.logger_config import test_logger as logger

@pytest.mark.nivel("bajo")
def test_database_connection():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1") ) # simple ping
        db.close()
        logger.info("Test de conexión a la base de datos exitosa.")
        assert True
    except OperationalError as e:
        logger.error(f"Error de conexión a la base de datos: {e}")
        assert False, "No se pudo conectar a la base de datos"
