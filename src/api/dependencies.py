# app/dependencies.py (ou onde preferir colocar suas dependências)

from typing import AsyncGenerator, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from . import security, schemas
from config import settings
from models.db import Professor, Administrador, LocalAsyncSession # Importe seus modelos e a sessão

# Esta instância aponta para a sua rota de login.
# O FastAPI a usará para saber de onde o token vem, especialmente na documentação interativa.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SECRET_KEY = settings.JWT.SECRET_KEY
ALGORITHM = settings.JWT.ALGORITHM

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with LocalAsyncSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            
async def get_current_active_user(
    token: str = Depends(oauth2_scheme), 
    session: AsyncSession = Depends(get_db_session)
) -> Union[Professor, Administrador]:
    """
    Decodifica o token JWT para obter o usuário atual e o retorna.
    Levanta uma exceção HTTPException 401 se o token for inválido ou o usuário não for encontrado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodifica o token usando nossa chave secreta e algoritmo
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )
        # O payload que criamos foi: {"sub": user.email, "role": role}
        # Mas o `jwt.decode` transforma em um dict.
        # Nosso "subject" era um dict, então precisamos acessá-lo.
        token_data_str = payload.get("sub")
        # Pequeno ajuste para garantir que o sub seja um dicionário
        # Em alguns casos, ele pode ser interpretado como string '{\'sub\': \'email\', ...}'
        import ast
        token_data = ast.literal_eval(token_data_str)

        email: str = token_data.get("sub")
        role: str = token_data.get("role")
        
        if email is None or role is None:
            raise credentials_exception
            
    except (JWTError, SyntaxError):
        raise credentials_exception

    # Busca o usuário no banco de dados com base no papel (role)
    user = None
    if role == "administrador":
        query = select(Administrador).where(Administrador.email == email)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
    elif role == "professor":
        query = select(Professor).where(Professor.email == email)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Aqui você poderia adicionar uma verificação se o usuário está ativo, se tivesse esse campo
    # if not user.is_active:
    #     raise HTTPException(status_code=400, detail="Usuário inativo")
        
    return user


