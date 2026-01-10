import os
import pytest
from fastapi import status
from sqlalchemy.orm import Session

from src.config import settings
from src.test.utils_common_methods import TestUtils

utils = TestUtils()

@pytest.mark.nivel("bajo")
@pytest.mark.usefixtures("client", "db_session")
def test_upload_player_photo_successfully(client, db_session: Session):
    # Arrange
    player_id = utils.create_player(client, "photo_user")

    # Act
    res = client.post(
        f"/player/photo_user/photo",
        files={
            "file": ("photo.png", b"fake-image-bytes", "image/png")
        }
    )

    # Assert response
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    assert body["username"] == "photo_user"
    assert "photo" in body

    # Assert file saved
    photo_path = os.path.join(
        settings.API_PHOTO_PLAYER_PATH_FOLDER,
        body["photo"]
    )
    assert os.path.exists(photo_path)

    # Cleanup
    os.remove(photo_path)

@pytest.mark.nivel("bajo")
@pytest.mark.usefixtures("client", "db_session")
def test_upload_player_photo_replaces_previous_photo(client, db_session: Session):
    utils.create_player(client, "photo_user")

    # Primera foto
    res1 = client.post(
        "/player/photo_user/photo",
        files={
            "file": ("a.png", b"first", "image/png")
        }
    )
    first_photo = res1.json()["photo"]
    first_path = os.path.join(
        settings.API_PHOTO_PLAYER_PATH_FOLDER,
        first_photo
    )
    assert os.path.exists(first_path)

    # Segunda foto
    res2 = client.post(
        "/player/photo_user/photo",
        files={
            "file": ("b.png", b"second", "image/png")
        }
    )
    second_photo = res2.json()["photo"]
    second_path = os.path.join(
        settings.API_PHOTO_PLAYER_PATH_FOLDER,
        second_photo
    )

    # Assert
    assert res2.status_code == status.HTTP_200_OK
    assert not os.path.exists(first_path)
    assert os.path.exists(second_path)

    # Cleanup
    os.remove(second_path)

@pytest.mark.nivel("bajo")
@pytest.mark.usefixtures("client", "db_session")
def test_upload_player_photo_too_large_should_fail(client, db_session: Session):
    utils.create_player(client, "photo_user")

    big_image = b"x" * (6 * 1024 * 1024)

    res = client.post(
        "/player/photo_user/photo",
        files={
            "file": ("photo.png", big_image, "image/png")
        }
    )

    assert res.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

@pytest.mark.nivel("bajo")
@pytest.mark.usefixtures("client", "db_session")
def test_upload_photo_for_nonexistent_player_should_fail(client, db_session: Session):
    res = client.post(
        "/player/no_such_user/photo",
        files={
            "file": ("photo.png", b"img", "image/png")
        }
    )

    assert res.status_code == status.HTTP_404_NOT_FOUND
