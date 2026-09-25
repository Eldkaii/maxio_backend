# Ejecutar: .venv\Scripts\python.exe releaser.py
import subprocess
import sys
import shutil
import stat
import time
from pathlib import Path
from datetime import datetime


# El script puede ejecutarse desde una consola Windows configurada en cp1252.
# Forzar UTF-8 evita que los mensajes informativos aborten el release.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# =========================
# Release metadata
# =========================
PROJECT = "maxio"
VERSION = "2.4.0"

PROJECT_NAME = f"{PROJECT}-{VERSION}"
ROOT_DIR = Path(__file__).resolve().parent
ENTRYPOINT = ROOT_DIR / "src" / "main.py"
CLOUDFLARED = ROOT_DIR / "tools" / "cloudflared.exe"

# =========================
# Helpers
# =========================
def run(cmd: list[str]):
    print(" ".join(cmd))
    subprocess.check_call(cmd)


def add_resource_args(cmd: list[str]) -> None:
    """Agrega recursos del release solo cuando existen en la rama actual."""
    resources = [
        ("--add-data", ROOT_DIR / "src" / "images", "images"),
        ("--add-data", ROOT_DIR / "src" / "fonts", "fonts"),
        ("--add-data", ROOT_DIR / "src" / "web", "web"),
        ("--add-data", ROOT_DIR / "src" / "bots_name", "."),
        ("--add-binary", CLOUDFLARED, "tools"),
    ]
    for option, source, destination in resources:
        if not source.exists():
            print(f"⚠️ Recurso no encontrado, se omite: {source}")
            continue
        cmd.extend([option, f"{source};{destination}"])


def remove_release_directory(path: Path) -> None:
    """Elimina build/dist y diagnostica bloqueos de Windows."""
    if not path.exists():
        return

    def make_writable(function, target, _error):
        try:
            Path(target).chmod(stat.S_IWRITE)
        except OSError:
            pass
        function(target)

    last_error = None
    for attempt in range(3):
        try:
            shutil.rmtree(path, onexc=make_writable)
            return
        except PermissionError as error:
            last_error = error
            if attempt < 2:
                time.sleep(1)

    raise RuntimeError(
        f"No se puede eliminar '{path}'. Cerrá el ejecutable de Maxio, "
        "cualquier consola ubicada en dist/ y el explorador que esté usando "
        "esa carpeta; luego volvé a ejecutar el release."
    ) from last_error

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
Maxio es una plataforma que combina una API REST, un bot de Telegram y
una interfaz conversacional de WhatsApp para la gestión de jugadores,
partidos, balanceo de equipos y
seguimiento de estadísticas y relaciones entre jugadores.

El sistema permite:
- Registrar y administrar jugadores
- Crear y gestionar partidos
- Balancear equipos automáticamente según estadísticas
- Registrar resultados y actualizar ELO
- Analizar relaciones entre jugadores (juntos / separados)
- Interactuar mediante un bot de Telegram
- Consultar jugadores, crear partidos y realizar evaluaciones desde WhatsApp

-------------------------------------------------
ARQUITECTURA (ALTO NIVEL)
-------------------------------------------------
- FastAPI: API REST principal
- PostgreSQL: Base de datos
- SQLAlchemy: ORM
- Bot de Telegram: Interfaz de usuario
- WhatsApp Cloud API: Webhook e interfaz conversacional
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

# WhatsApp Cloud API (requerido si se utilizara WhatsApp)
WHATSAPP_ACCESS_TOKEN=********
WHATSAPP_PHONE_NUMBER_ID=********
WHATSAPP_WABA_ID=********
META_APP_SECRET=********
WHATSAPP_WEBHOOK_VERIFY_TOKEN=********
WHATSAPP_GRAPH_API_VERSION=v23.0

# Tunel Cloudflare solo para pruebas locales de WhatsApp.
# APP_ENV=TEST activa el tunel incluido en el release.
# En produccion usar APP_ENV=PROD y un webhook HTTPS permanente.
APP_ENV=PROD
# CLOUDFLARE_TUNNEL_TOKEN=********

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
    root_env = ROOT_DIR / ".env"

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

    if not CLOUDFLARED.is_file():
        print(f"No se encontro Cloudflare Tunnel en: {CLOUDFLARED}")
        print("Copia cloudflared.exe a tools/ antes de generar el release")
        sys.exit(1)

    # Limpiar builds anteriores
    for folder in ["build", "dist"]:
        path = ROOT_DIR / folder
        if path.exists():
            print(f"🧹 Eliminando {folder}/")
            remove_release_directory(path)

    spec_file = ROOT_DIR / f"{PROJECT_NAME}.spec"
    if spec_file.exists():
        print(f"🧹 Eliminando {spec_file}")
        spec_file.unlink()

    print("📦 Generando ejecutable...")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--name", PROJECT_NAME,
        "--distpath", str(ROOT_DIR / "dist"),
        "--workpath", str(ROOT_DIR / "build"),
        "--specpath", str(ROOT_DIR),
    ]

    add_resource_args(cmd)
    cmd.append(str(ENTRYPOINT))

    run(cmd)

    dist_path = ROOT_DIR / "dist"
    generate_readme(dist_path)
    copy_env(dist_path)

    executable = dist_path / f"{PROJECT_NAME}.exe"
    if not executable.is_file():
        raise RuntimeError(f"PyInstaller no genero el ejecutable esperado: {executable}")

    print("\n✅ Release generado correctamente")
    print(f"📁 Ejecutable: dist/{PROJECT_NAME}.exe")
    print(f"📄 README: dist/README.txt")

if __name__ == "__main__":
    main()

