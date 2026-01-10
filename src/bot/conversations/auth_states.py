# src/bot/conversations/auth_states.py
from enum import Enum, auto

class AuthState(Enum):
    CHOOSING = auto()
    REGISTER_USERNAME = auto()
    REGISTER_EMAIL = auto()
    REGISTER_PASSWORD = auto()
