from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .. import schemas
from ..dependencies import get_db_session, get_current_active_user
from enums.tipo import PublicacaoTipoEnum
from models.db import Publicacao, Projeto, Professor, Administrador

router = APIRouter()

# ROTA 1: LISTAR TODAS AS PUBLICAÇÕES (PÚBLICA)
@router.get("/listar", response_model=List[schemas.PublicacaoResponse])
async def listar_publicacoes(session: AsyncSession = Depends(get_db_session)):
    query = (
        select(Publicacao)
        .order_by(Publicacao.data_publicacao.desc())
        .options(selectinload(Publicacao.professor), selectinload(Publicacao.projeto))
    )
    result = await session.execute(query)
    return result.scalars().all()

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
