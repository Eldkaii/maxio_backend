import requests

class AuthAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def login(self, username: str, password: str) -> str:
        url = f"{self.base_url}/auth/login"

        response = requests.post(
            url,
            json={
                "username": username,
                "password": password
            },
            timeout=5
        )

        if response.status_code != 200:
            raise Exception(response.text)

        return response.json()["access_token"]

