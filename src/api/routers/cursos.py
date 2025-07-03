from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .. import schemas
from ..dependencies import get_db_session, get_current_admin_user
from models.db import Administrador, Departamento, Curso

router = APIRouter()

@router.get(
    "/listar",
    response_model=List[schemas.CursoResponse],
    summary="Listar todos os cursos"
)
async def listar_cursos(session: AsyncSession = Depends(get_db_session)):
    """
    Lista todos os cursos cadastrados, incluindo o departamento e campus ao qual pertencem.
    Esta rota é pública.
    """
    query = (
        select(Curso)
        # Eager loading aninhado: carrega o departamento e, dentro dele, o campus
        .options(
            selectinload(Curso.departamento).selectinload(Departamento.campus)
        )
        .order_by(Curso.nome)
    )
    result = await session.execute(query)
    cursos = result.scalars().all()
    return cursos


# ROTA 2: CRIAR UM NOVO CURSO (ADMIN)
@router.post(
    "/criar",
    response_model=schemas.CursoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar um novo curso (Admin)"
)
async def criar_curso(
    dados_curso: schemas.CursoCreate,
    admin: Administrador = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Cria um novo curso vinculado a um departamento existente.
    Apenas administradores podem realizar esta ação.
    """
    # Verifica se o departamento informado existe
    departamento = await session.get(Departamento, dados_curso.departamento_id)
    if not departamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"O departamento com ID {dados_curso.departamento_id} não foi encontrado."
        )

    # Verifica se já existe um curso com o mesmo nome neste departamento
    query = select(Curso).where(
        Curso.nome == dados_curso.nome,
        Curso.departamento_id == dados_curso.departamento_id
    )
    if (await session.execute(query)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Um curso com este nome já existe neste departamento."
        )

    novo_curso = Curso(
        nome=dados_curso.nome,
        departamento_id=dados_curso.departamento_id
    )
    session.add(novo_curso)
    await session.commit()

    query_final = (
        select(Curso)
        .where(Curso.id == novo_curso.id)
        .options(
            # Carrega o departamento e, dentro dele, o campus
            selectinload(Curso.departamento).selectinload(Departamento.campus)
        )
    )
    curso_final = (await session.execute(query_final)).scalar_one()

    return curso_final
