from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TelegramWebAppLinkRequest(BaseModel):
    init_data: str


class TelegramWebAppAuthRequest(BaseModel):
    """Datos firmados que Telegram entrega al abrir una Mini App."""
    init_data: str
