import httpx
from src.config import settings
from src.schemas.user_schema import UserCreate
import requests


class UsersAPIClient:

    def __init__(self, token: str = None):
        self.base_url = settings.api_root
        self.base_url_login = settings.api_root_login
        self.token = token

    def register_user(self, payload: UserCreate) -> dict:
        url = f"{self.base_url}/users/register"

        with httpx.Client(timeout=10.0) as client:
            res = client.post(url, json=payload.model_dump())

        if res.status_code != 200:
            raise Exception(res.text)

        return res.json()

    def get_player(self, username: str):
        """
        Devuelve la información de un jugador dado su username usando /player/{username}
        """
        url = f"{self.base_url_login}/player/{username}"
        response = requests.get(url)
        if response.status_code == 404:
            raise ValueError(f"Jugador '{username}' no encontrado")
        response.raise_for_status()
        return response.json()

    def get_user(self):
        """
        Devuelve la información de un jugador dado su username usando /player/{username}
        """
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        url = f"{self.base_url}/users/me"
        response = requests.get(url,headers=headers)
        if response.status_code == 404:
            raise ValueError(f"Nadie se encuentra loggeado")
        response.raise_for_status()
        return response.json()

