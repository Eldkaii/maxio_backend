import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image
import os

from src.services.match_service import generate_match_card
from src.test.utils_common_methods import TestUtils
from src.config import settings

utils = TestUtils()


# @pytest.mark.nivel("bajo")
# def test_generate_match_card_dummy(db_session, client):
#     match, *_ = utils.setup_match_teams_players(client, db_session)
#
#     buffer = generate_match_card(match.id, db_session)
#
#     assert isinstance(buffer, BytesIO)
#

#
# @pytest.mark.nivel("medio")
# def test_generate_match_card_using_route(
#     client: TestClient,
#     db_session,
#     show_image: bool = True
# ):
#     """
#     Test que genera la card del match a través del endpoint.
#     """
#
#     match, *_ = utils.setup_match_teams_players(client, db_session)
#     match_id = match.id
#
#     # Llamar endpoint
#     response = client.post(f"/match/matches/{match_id}/match-card")
#
#     assert response.status_code == 200
#
#     buffer = BytesIO(response.content)
#
#     # Validaciones básicas
#     assert isinstance(buffer, BytesIO), "La respuesta debe ser un BytesIO"
#
#     img = Image.open(buffer)
#     assert img.mode == "RGBA", "La imagen debe estar en modo RGBA"
#
#     if show_image:
#         img.show()

@pytest.mark.nivel("alto")
def test_generate_match_card_with_real_template(
    client: TestClient,
    db_session,
    show_image: bool = True
):
    from src.utils.logger_config import test_logger as logger
    """
    Test unitario que genera la card del match usando el template real.
    """

    match, _, _, _, _, res_balance  = utils.setup_match_teams_players(client, db_session)
    match_id = match.id
    data = res_balance.json()
    logger.info(data)

    # Validar template
    assert os.path.exists(settings.API_MATCH_TEMPLATE_PATH), \
        f"Template no encontrado en {settings.API_MATCH_TEMPLATE_PATH}"

    # Generar card
    buffer: BytesIO = generate_match_card(match_id, db_session)

    # Validaciones básicas
    assert isinstance(buffer, BytesIO), "La función debe retornar un BytesIO"

    img = Image.open(buffer)
    assert img.mode == "RGBA", "La imagen debe estar en modo RGBA"

    if show_image:
        img.show()
