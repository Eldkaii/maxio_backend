"""No ORM access, no admin tokens, no Telegram/WhatsApp identities."""
import httpx


class Rejected(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__(f"API rechazó la acción (HTTP {status})")


class Api:
    def __init__(self, url):
        self.client = httpx.Client(base_url=url, timeout=20, trust_env=False)
        self.tokens = {}

    def close(self):
        self.client.close()

    def login(self, actor):
        response = self.client.post("/auth/login", json={
            "username": actor["username"], "password": actor["password"],
        })
        if response.status_code >= 400:
            raise Rejected(response.status_code)
        self.tokens[actor["username"]] = response.json()["access_token"]

    def request(self, method, path, payload=None, actor=None):
        # A 401 is a definite pre-mutation failure: renewing and retrying is safe.
        for attempt in range(2):
            headers = {}
            if actor:
                if actor["username"] not in self.tokens:
                    self.login(actor)
                headers["Authorization"] = "Bearer " + self.tokens[actor["username"]]
            response = self.client.request(method, path, json=payload, headers=headers)
            if response.status_code == 401 and actor and attempt == 0:
                self.tokens.pop(actor["username"], None)
                continue
            if 400 <= response.status_code < 500:
                raise Rejected(response.status_code)
            response.raise_for_status()
            return response.json() if response.content else None
