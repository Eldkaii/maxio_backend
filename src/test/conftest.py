import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker, Session
from src.main import app
from src.database import Base, get_db, engine

SessionLocal = sessionmaker(bind=engine)

# Cache para saber el nivel de cada item (necesario para reporte)
item_niveles_cache = {}

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    session = SessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

@pytest.fixture(scope="function", autouse=True)
def reset_database(db_session: Session):
    Base.metadata.drop_all(bind=db_session.get_bind())
    Base.metadata.create_all(bind=db_session.get_bind())
    yield
    db_session.commit()

# Marcas y niveles
niveles_ejecucion = ["bajo", "medio", "alto"]
estado_niveles = {nivel: {"passed": 0, "failed": 0, "skipped": 0} for nivel in niveles_ejecucion}
bloquear_niveles_superiores = set()
current_file = None

def pytest_configure(config):
    config.addinivalue_line("markers", "nivel(n): marca el test con un nivel: bajo, medio o alto")

def get_nivel(item):
    marca = item.get_closest_marker("nivel")
    return marca.args[0] if marca else "bajo"

def pytest_collection_modifyitems(session, config, items):
    # Guardamos el nivel de cada item en un cache
    for item in items:
        nivel = get_nivel(item)
        item_niveles_cache[item.nodeid] = nivel

    # Ordenamos por el nivel
    items.sort(key=lambda item: niveles_ejecucion.index(get_nivel(item)))

def pytest_runtest_setup(item):
    item_nivel = get_nivel(item)
    item.nivel = item_nivel

    if item_nivel in bloquear_niveles_superiores:
        pytest.skip(f"Tests del nivel '{item_nivel}' fueron bloqueados porque un test anterior falló")

def pytest_runtest_logstart(nodeid, location):
    global current_file
    test_file = nodeid.split("::")[0]
    test_name = nodeid.split("::")[-1]

    if test_file != current_file:
        current_file = test_file
        print(f"\n\n\n\033[1;44m====================================================\033[0m")
        print(f"\n\033[1;44m========== Archivo de Test: {test_file} ==========\033[0m")
        print(f"\n\033[1;44m====================================================\033[0m")

    print(f"\n\n\033[1;47m\033[30m>>> Ejecutando test: {test_name} <<<\033[0m")

def pytest_runtest_logreport(report):
    if report.when != "call":
        return

    test_name = report.nodeid.split("::")[-1]
    nivel = item_niveles_cache.get(report.nodeid, "bajo")
    resultado = report.outcome.upper()

    # Colores según resultado
    color_code = {
        "PASSED": "\033[1;42m\033[30m",  # fondo verde, texto negro
        "FAILED": "\033[1;41m\033[37m",  # fondo rojo, texto blanco
        "ERRORES": "\033[1;41m\033[37m",  # fondo rojo, texto blanco
        "SKIPPED": "\033[1;43m\033[30m",  # fondo amarillo, texto negro
    }.get(resultado, "\033[1;47m\033[30m")  # por defecto: fondo gris claro, texto negro

    reset = "\033[0m"
    print(
        f"{color_code}[RESULTADO] Test '{test_name}' del nivel '{nivel}' => {resultado}{reset}"
    )
    # Acumulamos resultados
    estado = estado_niveles[nivel]

    if report.when == "setup" and report.failed:
        estado["errores"] += 1
    if report.passed:
        estado["passed"] += 1
    elif report.failed:
        estado["failed"] += 1
        # Bloquear niveles siguientes
        idx = niveles_ejecucion.index(nivel)
        for superior in niveles_ejecucion[idx + 1:]:
            bloquear_niveles_superiores.add(superior)
    elif report.skipped:
        estado["skipped"] += 1

def pytest_terminal_summary(terminalreporter, exitstatus):
    print("\n\033[1;100m========= RESUMEN POR NIVEL =========\033[0m")
    for nivel in niveles_ejecucion:
        stats = estado_niveles[nivel]
        total = stats["passed"] + stats["failed"] + stats["skipped"]
        print(f"Nivel: {nivel.upper()} - Total: {total} | "
              f"\033[92m✔ {stats['passed']}\033[0m  "
              f"\033[91m✘ {stats['failed']}\033[0m  "
              f"\033[93m➖ {stats['skipped']}\033[0m")
