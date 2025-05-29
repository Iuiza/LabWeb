# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # Conveniente para login
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .. import schemas
from ..dependencies import get_db_session
# from ..core.security import create_access_token # Sua implementação
from models.db import Administrador # Importar o modelo de Administrador

router = APIRouter()

@router.post("/login", response_model=schemas.Token, summary="Login de Usuário")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Autentica um usuário (professor ou administrador) e retorna um token de acesso.
    O campo 'username' do formulário é o email.
    """
    
    result_obj = await (await session.execute(
        select(Administrador).where(
            Administrador.email == form_data.username,
            Administrador.senha == form_data.password
        )
    ))
    user = result_obj.scalar_one()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Determinar o papel do usuário para o token
    role = "administrador" if isinstance(user, schemas.AdministradorResponse) else "professor"
    
    # access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # access_token = create_access_token(
    #     data={"sub": user.email, "role": role}, expires_delta=access_token_expires
    # )
    # Placeholder para o token:
    access_token = f"fake_token_for_{role}_{user.email}"
    return {"access_token": access_token, "token_type": "bearer"}