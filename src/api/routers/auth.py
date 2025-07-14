from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Union

from .. import schemas
from ..dependencies import get_db_session, get_current_active_user
from models.db import Administrador, Professor # Importar ambos os modelos
from .. import security
from config import settings

ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT.ACCESS_TOKEN_EXPIRE_MINUTES

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
    user = None
    role = None

    # 1. Tenta encontrar o usuário como Administrador
    admin_result = await session.execute(
        select(Administrador).where(Administrador.email == form_data.username)
    )
    user_admin = admin_result.scalar_one_or_none()

    if user_admin:
        # Verifica a senha do administrador
        if security.verify_password(form_data.password, user_admin.senha):
            user = user_admin
            role = "administrador"
    
    # 2. Se não for admin, tenta encontrar como Professor
    if not user:
        professor_result = await session.execute(
            select(Professor).where(Professor.email == form_data.username)
        )
        user_professor = professor_result.scalar_one_or_none()
        
        if user_professor:
            # Verifica a senha do professor
            if security.verify_password(form_data.password, user_professor.senha):
                user = user_professor
                role = "professor"

    # 3. Se não encontrou usuário ou a senha não bateu
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 4. Cria o token de acesso com o papel (role) e o email (sub)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # O "subject" do token conterá o email e o papel para uso futuro
    token_data = {"sub": user.email, "role": role}
    access_token = security.create_access_token(
        subject=token_data, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get(
    "/me",
    response_model=schemas.MeResponse,
    summary="Obter dados do usuário logado"
)
async def read_users_me(
    current_user: Union[Professor, Administrador] = Depends(get_current_active_user)
):
    """
    Retorna os dados e o papel (role) do usuário
    atualmente autenticado.
    """
    role = "administrador" if isinstance(current_user, Administrador) else "professor"

    return {"role": role, "user_data": current_user}
