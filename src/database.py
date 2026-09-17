# src/database.py
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from src.config import settings
from src.utils.logger_config import app_logger as logger

engine = create_engine(settings.DATABASE_URL, echo=False)  # usamos logger, no echo

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    import src.models
    logger.info("Creando tablas en la base de datos (si no existen)...")
    Base.metadata.create_all(bind=engine)
    # Compatibilidad con bases existentes creadas antes de los datos de perfil.
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    additions = {
        "first_name": "VARCHAR(80) NOT NULL DEFAULT ''",
        "last_name": "VARCHAR(80) NOT NULL DEFAULT ''",
        "nationality": "VARCHAR(2) NOT NULL DEFAULT 'UY'",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))
    logger.info("Tablas creadas correctamente.")

# Esta es la función que FastAPI usará para inyectar la sesión en cada endpoint
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
