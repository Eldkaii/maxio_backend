# Ejecutar: .venv\Scripts\python.exe releaser.py
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime

# =========================
# Release metadata
# =========================
PROJECT = "maxio"
VERSION = "2.3.0"

PROJECT_NAME = f"{PROJECT}-{VERSION}"
ENTRYPOINT = "src/main.py"

# =========================
# Helpers
# =========================
def run(cmd: list[str]):
    print(" ".join(cmd))
    subprocess.check_call(cmd)


def add_resource_args(cmd: list[str]) -> None:
    """Agrega recursos solo si existen en la rama que se está compilando."""
    resources = [
        ("--add-data", Path("src/images"), "images"),
        ("--add-data", Path("src/fonts"), "fonts"),
        ("--add-data", Path("src/web"), "web"),
        ("--add-data", Path("src/bots_name"), "."),
        ("--add-binary", Path("tools/cloudflared.exe"), "tools"),
    ]
    for option, source, destination in resources:
        if not source.exists():
            print(f"⚠️ Recurso no encontrado, se omite: {source}")
            continue
        # PyInstaller usa ';' como separador origen/destino en Windows.
        cmd.extend([option, f"{source};{destination}"])

# =========================
# README generator
# =========================
def generate_readme(dist_path: Path):
    readme_content = f"""
MAXIO – Match & Player Intelligence Organizer
=============================================

Version: {VERSION}
Build date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

-------------------------------------------------
¿QUÉ ES MAXIO?
-------------------------------------------------
Maxio es una plataforma que combina una API REST y un bot de Telegram
para la gestión de jugadores, partidos, balanceo de equipos y
seguimiento de estadísticas y relaciones entre jugadores.

El sistema permite:
- Registrar y administrar jugadores
- Crear y gestionar partidos
- Balancear equipos automáticamente según estadísticas
- Registrar resultados y actualizar ELO
- Analizar relaciones entre jugadores (juntos / separados)
- Interactuar mediante un bot de Telegram

-------------------------------------------------
ARQUITECTURA (ALTO NIVEL)
-------------------------------------------------
- FastAPI: API REST principal
- PostgreSQL: Base de datos
- SQLAlchemy: ORM
- Bot de Telegram: Interfaz de usuario
- Uvicorn: Servidor ASGI

API y bot corren en el mismo proceso.

-------------------------------------------------
REQUISITOS DEL SISTEMA
-------------------------------------------------
- Windows 64 bits
- PostgreSQL instalado y en ejecución
- Puerto 8000 disponible
- Conexión a Internet (Telegram)

NO es necesario instalar:
- Python
- pip
- Librerías adicionales

-------------------------------------------------
CONFIGURACIÓN
-------------------------------------------------
1) Crear un archivo `.env` en la misma carpeta que el ejecutable
2) Completar las siguientes variables:

DB_HOST=localhost
DB_PORT=5432
DB_NAME=maxiodb
DB_USER=maxio
DB_PASSWORD=********
TELEGRAM_TOKEN=********

-------------------------------------------------
EJECUCIÓN
-------------------------------------------------
- Ejecutar `{PROJECT_NAME}.exe`
- Se abrirá una consola mostrando los logs
- API disponible en:
  http://localhost:8000/maxio

-------------------------------------------------
LOGS
-------------------------------------------------
- Los logs se muestran por consola
- También se guarda el archivo:
  maxio.log

-------------------------------------------------
NOTAS
-------------------------------------------------
- El bot de Telegram se inicia automáticamente
- La base de datos se inicializa al arranque
- El proceso se detiene cerrando la consola

-------------------------------------------------
"""

    readme_path = dist_path / "README.txt"
    readme_path.write_text(readme_content.strip(), encoding="utf-8")

# =========================
# copiar ENV
# =========================
def copy_env(dist_path: Path):
    root_env = Path(".env")

    if not root_env.exists():
        print("⚠️  No se encontró archivo .env en la raíz del proyecto")
        print("👉 Se generará el release SIN archivo .env")
        return

    dist_env = dist_path / ".env"
    shutil.copy2(root_env, dist_env)
    print("🔐 Archivo .env copiado a dist/")

# =========================
# Main release flow
# =========================
def main():
    print("🚀 Iniciando proceso de liberación de Maxio")

    # Verificar PyInstaller
    try:
        import PyInstaller  # noqa
    except ImportError:
        print("❌ PyInstaller no está instalado")
        print("👉 Ejecutá: pip install pyinstaller")
        sys.exit(1)

    # Limpiar builds anteriores
    for folder in ["build", "dist"]:
        path = Path(folder)
        if path.exists():
            print(f"🧹 Eliminando {folder}/")
            shutil.rmtree(path)

    spec_file = Path(f"{PROJECT_NAME}.spec")
    if spec_file.exists():
        print(f"🧹 Eliminando {spec_file}")
        spec_file.unlink()

    print("📦 Generando ejecutable...")

    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", PROJECT_NAME,
    ]
    add_resource_args(cmd)
    cmd.append(ENTRYPOINT)

    run(cmd)

    dist_path = Path("dist")
    generate_readme(dist_path)
    copy_env(dist_path)

    print("\n✅ Release generado correctamente")
    print(f"📁 Ejecutable: dist/{PROJECT_NAME}.exe")
    print(f"📄 README: dist/README.txt")

if __name__ == "__main__":
    main()
