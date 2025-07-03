# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Union

from jose import jwt
from passlib.context import CryptContext

from config import settings

ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT.ACCESS_TOKEN_EXPIRE_MINUTES
SECRET_KEY = settings.JWT.SECRET_KEY
ALGORITHM = settings.JWT.ALGORITHM

# Contexto para hash de senhas usando o algoritmo Bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """Cria o hash de uma senha."""
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    """
    Cria um token de acesso JWT.
    :param subject: O assunto (identificador) do token, como o email do usuário.
    :param expires_delta: Tempo de vida do token.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Usa o tempo de expiração padrão das configurações
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
