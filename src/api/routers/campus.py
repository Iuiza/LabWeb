from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .. import schemas
from ..dependencies import get_db_session, get_current_admin_user
from models.db import Administrador, Campus

router = APIRouter()

@router.get(
    "/listar",
    response_model=List[schemas.CampusResponse],
    summary="Listar todos os campus"
)
async def listar_campus(session: AsyncSession = Depends(get_db_session)):
    """
    Lista todos os campus cadastrados, ordenados por nome.
    Esta rota é pública.
    """
    query = select(Campus).order_by(Campus.nome)
    result = await session.execute(query)
    campi = result.scalars().all()
    return campi

@router.post(
    "/criar",
    response_model=schemas.CampusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar um novo campus (Admin)"
)
async def criar_campus(
    dados_campus: schemas.CampusCreate,
    admin: Administrador = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Cria um novo campus no sistema.
    Apenas administradores podem realizar esta ação.
    """
    # Verifica se o campus já existe para evitar duplicatas
    query = select(Campus).where(Campus.nome == dados_campus.nome)
    campus_existente = (await session.execute(query)).scalar_one_or_none()
    if campus_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Um campus com este nome já existe."
        )

    novo_campus = Campus(nome=dados_campus.nome)
    session.add(novo_campus)
    await session.commit()
    await session.refresh(novo_campus)

    return novo_campus
