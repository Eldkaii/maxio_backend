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
    league_member_columns = {column["name"] for column in inspect(engine).get_columns("league_members")}
    additions = {
        "first_name": "VARCHAR(80) NOT NULL DEFAULT ''",
        "last_name": "VARCHAR(80) NOT NULL DEFAULT ''",
        "nationality": "VARCHAR(2) NOT NULL DEFAULT 'UY'",
        "is_admin": "BOOLEAN NOT NULL DEFAULT FALSE",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))
        match_columns = {column["name"] for column in inspect(engine).get_columns("matches")}
        if "league_id" not in match_columns:
            connection.execute(text(
                "ALTER TABLE matches ADD COLUMN league_id INTEGER REFERENCES leagues(id) ON DELETE SET NULL"
            ))
        league_column_metadata = inspect(engine).get_columns("leagues")
        league_columns = {column["name"] for column in league_column_metadata}
        if "is_public" not in league_columns:
            connection.execute(text("ALTER TABLE leagues ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT FALSE"))
        if "is_system_managed" not in league_columns:
            connection.execute(text("ALTER TABLE leagues ADD COLUMN is_system_managed BOOLEAN NOT NULL DEFAULT FALSE"))
        if "is_special" not in league_columns:
            connection.execute(text("ALTER TABLE leagues ADD COLUMN is_special BOOLEAN NOT NULL DEFAULT FALSE"))
        league_member_additions = {
            "is_pinned": "BOOLEAN NOT NULL DEFAULT FALSE",
            "points": "INTEGER NOT NULL DEFAULT 0",
            "matches_played": "INTEGER NOT NULL DEFAULT 0",
            "wins": "INTEGER NOT NULL DEFAULT 0",
            "losses": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, definition in league_member_additions.items():
            if name not in league_member_columns:
                connection.execute(text(f"ALTER TABLE league_members ADD COLUMN {name} {definition}"))
        if "country_code" not in league_columns:
            connection.execute(text("ALTER TABLE leagues ADD COLUMN country_code VARCHAR(2)"))
        # Reutilizar los metadatos obtenidos antes de los ALTER TABLE. Consultar
        # inspect(engine) aquí abriría otra conexión que queda bloqueada por
        # esta misma transacción de migración.
        owner_column = next(column for column in league_column_metadata if column["name"] == "owner_player_id")
        if not owner_column["nullable"]:
            connection.execute(text("ALTER TABLE leagues ALTER COLUMN owner_player_id DROP NOT NULL"))
        # La unicidad de nombre y país aislado pertenecía a la primera versión
        # de ligas. Ahora solo país+modalidad es único; las especiales pueden
        # compartir nombre si las crea administración.
        connection.execute(text("ALTER TABLE leagues DROP CONSTRAINT IF EXISTS leagues_name_key"))
        connection.execute(text("ALTER TABLE leagues DROP CONSTRAINT IF EXISTS leagues_country_code_key"))
        connection.execute(text("DROP INDEX IF EXISTS ix_leagues_name"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_leagues_name ON leagues(name)"))
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_leagues_country_type "
            "ON leagues(country_code, league_type) WHERE country_code IS NOT NULL"
        ))
    logger.info("Tablas creadas correctamente.")

# Esta es la función que FastAPI usará para inyectar la sesión en cada endpoint
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
