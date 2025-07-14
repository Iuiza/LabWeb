from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from .. import schemas
from ..dependencies import get_db_session, get_current_active_user
from enums.tipo import PublicacaoTipoEnum
from models.db import Publicacao, Projeto, Professor, Administrador

router = APIRouter()

# ROTA 1: LISTAR TODAS AS PUBLICAÇÕES (PÚBLICA)
@router.get(
    "/listar",
    response_model=schemas.PaginatedPublicacaoResponse,
    summary="Listar, buscar e filtrar publicações"
)
async def listar_publicacoes(
    session: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 6,
    search: Optional[str] = None, # Parâmetro para busca por palavra-chave
    tipo: Optional[PublicacaoTipoEnum] = None, # Parâmetro para filtro por tipo
    projeto_id: Optional[int] = None, # Parâmetro para filtro por projeto
    curso_id: Optional[int] = None # Parâmetro para filtro por curso
):
    # Consulta base
    query = (
        select(Publicacao)
        .join(Publicacao.projeto) # Join para permitir filtro por curso
        .order_by(Publicacao.data_publicacao.desc())
    )

    # Aplica os filtros dinamicamente se eles forem fornecidos
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Publicacao.titulo.ilike(search_term),
                Publicacao.conteudo.ilike(search_term)
            )
        )
    if tipo:
        query = query.filter(Publicacao.tipo == tipo)
    if projeto_id:
        query = query.filter(Publicacao.projeto_id == projeto_id)
    if curso_id:
        query = query.filter(Projeto.curso_id == curso_id)

    # Primeiro, contamos o total de itens com os filtros aplicados
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Depois, aplicamos a paginação para a consulta final
    paginated_query = (
        query
        .offset(skip)
        .limit(limit)
        .options(selectinload(Publicacao.professor), selectinload(Publicacao.projeto))
    )
    
    result = await session.execute(paginated_query)
    publicacoes = result.scalars().unique().all()
    
    return {"total": total, "publicacoes": publicacoes}

# ROTA 2: EXIBIR UMA PUBLICAÇÃO ESPECÍFICA (PÚBLICA)
@router.get("/exibir/{publicacao_id}", response_model=schemas.PublicacaoResponse)
async def get_detalhes_publicacao(publicacao_id: int, session: AsyncSession = Depends(get_db_session)):
    query = (
        select(Publicacao)
        .where(Publicacao.id == publicacao_id)
        .options(selectinload(Publicacao.professor), selectinload(Publicacao.projeto))
    )
    publicacao = (await session.execute(query)).scalar_one_or_none()
    if not publicacao:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publicação não encontrada.")
    return publicacao

# ROTA 3: CRIAR UMA NOVA PUBLICAÇÃO (PRIVADA)
@router.post("/criar", response_model=schemas.PublicacaoResponse, status_code=status.HTTP_201_CREATED)
async def criar_publicacao(
    current_user: Union[Professor, Administrador] = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    titulo: str = Form(...),
    conteudo: str = Form(...),
    tipo: PublicacaoTipoEnum = Form(PublicacaoTipoEnum.NOTICIA),
    projeto_id: int = Form(...),
    imagem: Optional[UploadFile] = File(None),
):
    # RN-3: Cada notícia/evento deve estar vinculada a um projeto
    projeto = await session.get(Projeto, projeto_id, options=[selectinload(Projeto.link_professores)])
    if not projeto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")

    # Autorização: Professor só pode postar em projeto do qual é responsável
    if isinstance(current_user, Professor):
        professor_ids_do_projeto = {link.professor_id for link in projeto.link_professores}
        if current_user.id not in professor_ids_do_projeto:
            raise HTTPException(status_code=403, detail="Você não tem permissão para publicar neste projeto.")

    path_imagem_salva = f"static/images/publicacoes/{imagem.filename}" if imagem else None

    nova_publicacao = Publicacao(
        titulo=titulo,
        conteudo=conteudo,
        tipo=tipo,
        projeto_id=projeto_id,
        professor_id=current_user.id, # O autor é sempre o usuário logado
        path_imagem=path_imagem_salva
    )
    session.add(nova_publicacao)
    await session.commit()
    await session.refresh(nova_publicacao, ["professor", "projeto"]) # Recarrega as relações
    return nova_publicacao

# ROTA 4: EDITAR UMA PUBLICAÇÃO (PRIVADA)
@router.put("/editar/{publicacao_id}", response_model=schemas.PublicacaoResponse)
async def editar_publicacao(
    publicacao_id: int,
    current_user: Union[Professor, Administrador] = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    titulo: str = Form(...),
    conteudo: str = Form(...),
    tipo: PublicacaoTipoEnum = Form(...),
    projeto_id: int = Form(...),
    imagem: Optional[UploadFile] = File(None),
):
    publicacao = await session.get(Publicacao, publicacao_id)
    if not publicacao:
        raise HTTPException(status_code=404, detail="Publicação não encontrada.")

    # Autorização: Apenas o professor que criou a postagem ou um admin pode editar
    if isinstance(current_user, Professor) and publicacao.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta publicação.")

    # Atualiza os campos
    publicacao.titulo = titulo
    publicacao.conteudo = conteudo
    publicacao.tipo = tipo
    publicacao.projeto_id = projeto_id # Permite mover a publicação para outro projeto

    if imagem:
        publicacao.path_imagem = f"static/images/publicacoes/{imagem.filename}"
    
    await session.commit()
    await session.refresh(publicacao, ["professor", "projeto"])
    return publicacao

@router.get(
    "/me",
    response_model=schemas.PaginatedPublicacaoResponse,
    summary="Listar as publicações do usuário autenticado"
)
async def listar_minhas_publicacoes(
    current_user: Professor = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 9
):
    """
    Lista as publicações criadas pelo professor atualmente logado.
    """
    # Consulta para contar o total de publicações do usuário
    count_query = (
        select(func.count(Publicacao.id))
        .where(Publicacao.professor_id == current_user.id)
    )
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Consulta paginada para buscar as publicações do usuário
    query = (
        select(Publicacao)
        .where(Publicacao.professor_id == current_user.id)
        .order_by(Publicacao.data_publicacao.desc())
        .offset(skip)
        .limit(limit)
        .options(selectinload(Publicacao.professor), selectinload(Publicacao.projeto))
    )
    result = await session.execute(query)
    publicacoes = result.scalars().all()

    return {"total": total, "publicacoes": publicacoes}

@router.delete("/deletar/{publicacao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_publicacao(
    publicacao_id: int,
    current_user: Union[Professor, Administrador] = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Exclui uma publicação.
        
    O professor só pode excluir suas próprias publicações.
    O administrador pode excluir qualquer publicação."""
    publicacao = await session.get(Publicacao, publicacao_id)
    if not publicacao:
        raise HTTPException(status_code=404, detail="Publicação não encontrada.")

    # Lógica de autorização
    is_owner = isinstance(current_user, Professor) and publicacao.professor_id == current_user.id
    is_admin = isinstance(current_user, Administrador)

    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Você não tem permissão para excluir esta publicação.")

    await session.delete(publicacao)
    await session.commit()
    return None # Retorna uma resposta 204 No Content
