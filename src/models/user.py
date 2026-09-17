# src/models/user.py

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import validates, relationship
from ..database import Base
import bcrypt

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    first_name = Column(String(80), nullable=False, default="")
    last_name = Column(String(80), nullable=False, default="")
    nationality = Column(String(2), nullable=False, default="UY")
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # encriptada
    password_test = Column(String(255), nullable=False)  # encriptada

    player = relationship("Player", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, plain_password: str):
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
        self.password = hashed.decode('utf-8')
        self.password_test = plain_password

    def check_password(self, plain_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), self.password.encode('utf-8'))

    @validates("email")
    def validate_email(self, key, email):
        # if "@" not in email:
        #     raise ValueError("El email no es válido.")
        # return email
        return email
