# app/routers/professores.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Union
from sqlalchemy import select

from .. import schemas
from ..dependencies import get_db_session, get_current_active_user
from models.db import Professor, Administrador
from .. import security

router = APIRouter()

@router.get(
    "/listar",
    response_model=List[schemas.ProfessorResponse],
    summary="Listar todos os professores"
)
async def listar_professores(session: AsyncSession = Depends(get_db_session)):
    """
    Lista todos os professores cadastrados.
    Esta rota é pública e não requer autenticação.
    """
    query = select(Professor).order_by(Professor.nome)
    result = await session.execute(query)
    professores = result.scalars().all()
    return professores

@router.put(
    "/me/mudar-senha",
    status_code=status.HTTP_200_OK,
    summary="Alterar a própria senha"
)
async def mudar_propria_senha(
    dados_senha: schemas.PasswordChange,
    session: AsyncSession = Depends(get_db_session),
    current_user: Union[Professor, Administrador] = Depends(get_current_active_user)
):
    """
    Permite que um professor autenticado altere sua própria senha.
    O usuário deve fornecer a senha antiga e a nova.
    """
    # Garante que apenas um professor está usando esta rota
    if not isinstance(current_user, Professor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas professores podem alterar a própria senha por esta rota."
        )

    # 1. Verifica se a senha antiga está correta
    if not security.verify_password(dados_senha.senha_antiga, current_user.senha):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha antiga está incorreta."
        )

    # 2. Cria o hash da nova senha
    hash_nova_senha = security.hash_password(dados_senha.senha_nova)

    # 3. Atualiza a senha no objeto do usuário e salva no banco
    current_user.senha = hash_nova_senha
    session.add(current_user)
    await session.commit()

    return {"detail": "Senha alterada com sucesso."}