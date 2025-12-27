import pytest
from _pytest import pathlib
from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image
import os

from src.test.utils_common_methods import TestUtils
from src.services.player_service import generate_player_card_from_player  # versión unitaria que recibe Player
from src.config import settings

utils = TestUtils()

@pytest.fixture
def seed_single_player(client: TestClient):
    utils.create_player(
        client,
        "TestPlayer",
        stats={
            'tiro': 60, 'ritmo': 30, 'fisico': 65,
            'defensa': 50, 'aura': 80
        }
    )
    yield

@pytest.mark.nivel("medio")
def test_generate_player_card_with_real_template(client: TestClient, seed_single_player, show_image: bool = True):
    """
    Test que genera la carta usando el template real.
    Guarda la carta en src/images/carta_test.png y permite inspección visual.
    """

    # Obtener datos del jugador
    player_data = utils.get_player(client, "TestPlayer")

    # DummyPlayer que refleja el modelo real
    class DummyPlayer:
        def __init__(self, data, photo_path=None):
            self.id = data.get("id")
            self.name = data["name"]
            self.cant_partidos = data.get("cant_partidos", 0)
            self.cant_partidos_ganados = data.get("cant_partidos_ganados", 0)
            self.is_bot = data.get("is_bot", False)
            self.recent_results = data.get("recent_results", [])
            self.elo = data.get("elo", 1000)
            # Stats individuales
            self.tiro = data.get("tiro", 50)
            self.ritmo = data.get("ritmo", 50)
            self.fisico = data.get("fisico", 50)
            self.defensa = data.get("defensa", 50)
            self.aura = data.get("aura", 50)
            self.photo_path = photo_path

    # Crear foto temporal del jugador
    photo_path = os.path.join("src", "images","random_faces","random1.png")
    #os.makedirs(os.path.dirname(photo_path), exist_ok=True)
    #Image.new("RGBA", (200, 250), (255, 0, 0, 255)).save(photo_path)

    photo_path = 'C:\Proyectos\Max_io\src\images\\random_faces\\random3.png'
    player = DummyPlayer(player_data, photo_path=photo_path)

    #template_path = pathlib.Path(__file__).parent.parent / "images" / "template.png"
    #assert template_path.exists(), f"Template no encontrado en {template_path}"
    #assert os.path.exists(template_path), f"Template no encontrado en {template_path}"

    # Generar carta
    buffer: BytesIO = generate_player_card_from_player(player)
    #img = Image.open(buffer)
    #img.show()  # verifica visualmente el template

    # Validaciones básicas
    assert isinstance(buffer, BytesIO), "La función debe retornar un BytesIO"
    img = Image.open(buffer)
    assert img.mode == "RGBA", "La imagen debe estar en modo RGBA"

    # Guardar la carta final en el proyecto
    #base_folder = settings.API_PHOTO_PLAYER_PATH_FOLDER
    #output_path = os.path.join(base_folder,"src", "images", "carta_test.png")
    #img.save(output_path)
    #print(f"Carta generada con template real guardada en: {output_path}")

    # Abrir la carta opcionalmente
    if show_image:
        img.show()

@pytest.mark.nivel("medio")
def test_generate_player_card_with_real_template_using_route(client: TestClient, seed_single_player, show_image: bool = True):
    """
    Test que genera la carta usando el template real.
    Guarda la carta en src/images/carta_test.png y permite inspección visual.
    """
    utils.create_player(client, "Bot1")


    # Crear foto temporal del jugador
    photo_path = os.path.join("src", "images","random_faces","random1.png")
    #os.makedirs(os.path.dirname(photo_path), exist_ok=True)
    #Image.new("RGBA", (200, 250), (255, 0, 0, 255)).save(photo_path)

    photo_path = 'C:\Proyectos\Max_io\src\images\\random_faces\\random3.png'
    player = utils.get_player(client,'Bot1')
    player['photo_path'] = photo_path

    template_path = pathlib.Path(__file__).parent.parent / "images" / "template.png"
    assert template_path.exists(), f"Template no encontrado en {template_path}"
    assert os.path.exists(template_path), f"Template no encontrado en {template_path}"

    # Generar carta
    response = client.get("/player/Bot1/card")
    assert response.status_code == 200

    buffer = BytesIO(response.content)    #img = Image.open(buffer)
    #img.show()  # verifica visualmente el template

    # Validaciones básicas
    assert isinstance(buffer, BytesIO), "La función debe retornar un BytesIO"
    img = Image.open(buffer)
    assert img.mode == "RGBA", "La imagen debe estar en modo RGBA"

    # Guardar la carta final en el proyecto
    #output_path = os.path.join("src", "images", "carta_test.png")
    #img.save(output_path)
    #print(f"Carta generada con template real guardada en: {output_path}")

    # Abrir la carta opcionalmente
    if show_image:
        img.show()