from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .. import schemas
from ..dependencies import get_db_session, get_current_admin_user
from models.db import Administrador, Campus, Departamento

router = APIRouter()

# ROTA 1: LISTAR TODOS OS DEPARTAMENTOS (PÚBLICA)
@router.get(
    "/",
    response_model=List[schemas.DepartamentoResponse],
    summary="Listar todos os departamentos"
)
async def listar_departamentos(session: AsyncSession = Depends(get_db_session)):
    """
    Lista todos os departamentos cadastrados, incluindo o campus ao qual pertencem.
    Esta rota é pública.
    """
    query = (
        select(Departamento)
        .options(selectinload(Departamento.campus)) # Carrega os dados do campus junto
        .order_by(Departamento.nome)
    )
    result = await session.execute(query)
    departamentos = result.scalars().all()
    return departamentos


# ROTA 2: CRIAR UM NOVO DEPARTAMENTO (ADMIN)
@router.post(
    "/",
    response_model=schemas.DepartamentoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar um novo departamento (Admin)"
)
async def criar_departamento(
    dados_departamento: schemas.DepartamentoCreate,
    admin: Administrador = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Cria um novo departamento vinculado a um campus existente.
    Apenas administradores podem realizar esta ação.
    """
    # Verifica se o campus informado existe
    campus = await session.get(Campus, dados_departamento.campus_id)
    if not campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"O campus com ID {dados_departamento.campus_id} não foi encontrado."
        )

    # Verifica se já existe um departamento com o mesmo nome neste campus
    query = select(Departamento).where(
        Departamento.nome == dados_departamento.nome,
        Departamento.campus_id == dados_departamento.campus_id
    )
    if (await session.execute(query)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Um departamento com este nome já existe neste campus."
        )

    novo_departamento = Departamento(
        nome=dados_departamento.nome,
        campus_id=dados_departamento.campus_id
    )
    session.add(novo_departamento)
    await session.commit()
    # Recarrega o objeto para incluir o relacionamento com o campus na resposta
    await session.refresh(novo_departamento, ["campus"])
    
    return novo_departamento
