from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from .. import schemas
from ..dependencies import get_db_session, get_current_active_user
from enums.status import ProjetoStatusEnum
from models.db import Projeto, Professor, Administrador, ProjetoProfessor, Curso, Departamento

router = APIRouter()

# RF-2: PERMITIR QUE PROFESSORES E ADMINISTRADORES CADASTREM NOVOS PROJETOS
@router.post(
    "/criar",
    response_model=schemas.ProjetoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo projeto de extensão"
)
async def criar_novo_projeto(
    # Dependências
    session: AsyncSession = Depends(get_db_session),
    current_user: Union[Professor, Administrador] = Depends(get_current_active_user),
    
    # Dados do Formulário
    titulo: str = Form(...),
    descricao: Optional[str] = Form(None),
    data_inicio: datetime = Form(...),
    data_fim: Optional[datetime] = Form(None),
    status: ProjetoStatusEnum = Form(ProjetoStatusEnum.ATIVO),
    publico: str = Form(...),
    curso_id: int = Form(...),
    professor_ids_responsaveis: List[int] = Form(...),
    imagem_capa: Optional[UploadFile] = File(None)
):
    """
    Cria um novo projeto de extensão. 
    Apenas professores e administradores autenticados podem realizar esta ação. 
    Verifica se o título do projeto já foi usado por um projeto ativo. 
    """
    # 1. VERIFICAR TÍTULO DUPLICADO (RF-2)
    query_titulo_existente = select(Projeto).where(
        and_(
            Projeto.titulo == titulo,
            Projeto.status == ProjetoStatusEnum.ATIVO
        )
    )
    result = await session.execute(query_titulo_existente)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Já existe um projeto ativo com este título."
        )

    # 2. APLICAR REGRAS DE NEGÓCIO BASEADAS NO PAPEL (ROLE)
    if isinstance(current_user, Professor):
        # RN: O professor que está criando o projeto DEVE estar na lista de responsáveis. 
        if current_user.id not in professor_ids_responsaveis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="O professor que cria o projeto deve estar na lista de responsáveis."
            )

    # (Opcional, mas recomendado) Verificar se os IDs dos professores responsáveis existem
    query_professores = select(Professor).where(Professor.id.in_(professor_ids_responsaveis))
    professores_result = await session.execute(query_professores)
    professores_encontrados = professores_result.scalars().all()
    if len(professores_encontrados) != len(set(professor_ids_responsaveis)):
        raise HTTPException(status_code=404, detail="Um ou mais IDs de professores responsáveis não foram encontrados.")

    # 3. Lógica para salvar a imagem (se houver)
    path_imagem_salva = None
    if imagem_capa:
        # A implementação real de `save_upload_file` é recomendada
        # path_imagem_salva = await save_upload_file(imagem_capa, "projetos")
        path_imagem_salva = f"static/images/projetos/{imagem_capa.filename}" # Placeholder

        novo_projeto = Projeto(
        titulo=titulo,
        descricao=descricao,
        path_imagem=path_imagem_salva,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=status.value,
        publico=publico,
        curso_id=curso_id
    )

    # 2. Crie as associações na tabela projeto_professor
    # Adicionamos o projeto primeiro para que ele tenha um estado 'pending' na sessão
    session.add(novo_projeto)

    for prof_id in professor_ids_responsaveis:
        # Cria a linha na tabela de associação
        associacao = ProjetoProfessor(
            projeto=novo_projeto,  # Associa o objeto Projeto
            professor_id=prof_id  # Associa o ID do Professor
        )
        session.add(associacao)

    # 3. Agora, comita a transação
    # Isso salvará o novo projeto e todas as novas associações de uma vez.
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        # Verificar se um dos IDs de professor não existe pode causar um IntegrityError aqui
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Erro ao salvar: um dos IDs de professor pode não existir. Detalhe: {e}"
        )

    # 4. Refresque o objeto para carregar as relações antes de retornar
    # Usamos o eager loading para garantir que a resposta Pydantic não cause erros
    query_final = (
        select(Projeto)
        .where(Projeto.id == novo_projeto.id)
        .options(
            selectinload(Projeto.curso),
            # Carrega através da tabela de associação
            selectinload(Projeto.link_professores).selectinload(ProjetoProfessor.professor)
        )
    )
    projeto_final = (await session.execute(query_final)).scalar_one()

    return projeto_final

@router.get(
    "/listar",
    response_model=schemas.PaginatedProjetoResponse,
    summary="Listar todos os projetos de extensão"
)
async def listar_projetos(
    session: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 8 # Itens por página, ex: 8 para um grid 4x2
):
    """
    Lista todos os projetos de extensão de forma paginada.
    """
    # Consulta para contar o total de projetos
    count_query = select(func.count(Projeto.id))
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Consulta para buscar a página atual de projetos
    query = (
        select(Projeto)
        .order_by(Projeto.data_inicio.desc())
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(Projeto.curso).selectinload(Curso.departamento).selectinload(Departamento.campus),
            selectinload(Projeto.link_professores).selectinload(ProjetoProfessor.professor),
            selectinload(Projeto.publicacoes)
        )
    )
    result = await session.execute(query)
    projetos = result.scalars().unique().all()

    return {"total": total, "items": projetos}

@router.get(
    "/exibir/{projeto_id}",
    response_model=schemas.ProjetoResponse,
    summary="Obter detalhes públicos de um projeto específico"
)
async def get_detalhes_projeto(
    projeto_id: int,
    session: AsyncSession = Depends(get_db_session)
    # REMOVEMOS a dependência 'current_user' para tornar a rota pública
):
    """
    Obtém os dados detalhados de um único projeto.
    Esta rota é pública e pode ser acessada por qualquer visitante. 
    """
    # A lógica de busca e eager loading continua a mesma
    query = (
        select(Projeto)
        .where(Projeto.id == projeto_id)
        .options(
            selectinload(Projeto.curso).selectinload(Curso.departamento).selectinload(Departamento.campus),
            selectinload(Projeto.link_professores).selectinload(ProjetoProfessor.professor),
            selectinload(Projeto.publicacoes)
        )
    )
    projeto = (await session.execute(query)).scalar_one_or_none()

    # Se o projeto com o ID fornecido não existir, retorna um erro 404
    if not projeto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    
    return projeto

# 2. ROTA PARA SALVAR AS INFORMAÇÕES EDITADAS
@router.put(
    "/editar/{projeto_id}",
    response_model=schemas.ProjetoResponse,
    summary="Editar um projeto de extensão"
)
async def editar_projeto(
    projeto_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: Union[Professor, Administrador] = Depends(get_current_active_user),
    # Os dados vêm do formulário de edição, assim como na criação
    titulo: str = Form(...),
    descricao: Optional[str] = Form(None),
    data_inicio: datetime = Form(...),
    data_fim: Optional[datetime] = Form(None),
    status: ProjetoStatusEnum = Form(...),
    publico: str = Form(...),
    curso_id: int = Form(...),
    professor_ids_responsaveis: List[int] = Form(...),
    imagem_capa: Optional[UploadFile] = File(None) # Opcional: para alterar a imagem
):
    """
    Permite que professores e administradores editem as informações do projeto. 
    - Um professor só pode editar um projeto se for um dos responsáveis.
    - Um administrador pode editar qualquer projeto.
    """
    # Busca o projeto existente no banco
    projeto_a_editar = await session.get(Projeto, projeto_id, options=[selectinload(Projeto.link_professores)])

    if not projeto_a_editar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")

    # Lógica de autorização para edição
    if isinstance(current_user, Professor):
        professor_ids_do_projeto = {link.professor_id for link in projeto_a_editar.link_professores}
        if current_user.id not in professor_ids_do_projeto:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para editar este projeto."
            )

    # Lógica para lidar com a imagem (se uma nova for enviada)
    if imagem_capa:
        # Aqui você pode adicionar lógica para deletar a imagem antiga e salvar a nova
        path_imagem_salva = f"static/images/projetos/{imagem_capa.filename}"
        projeto_a_editar.path_imagem = path_imagem_salva

    # Atualiza os campos do projeto com os novos dados
    projeto_a_editar.titulo = titulo
    projeto_a_editar.descricao = descricao
    projeto_a_editar.data_inicio = data_inicio
    projeto_a_editar.data_fim = data_fim
    projeto_a_editar.status = status.value
    projeto_a_editar.publico = publico
    projeto_a_editar.curso_id = curso_id

    # Atualiza os professores responsáveis (abordagem: remover antigos, adicionar novos)
    # 1. Remove as associações antigas
    for link in projeto_a_editar.link_professores:
        await session.delete(link)
    
    # 2. Cria as novas associações
    novas_associacoes = [
        ProjetoProfessor(projeto_id=projeto_id, professor_id=prof_id)
        for prof_id in professor_ids_responsaveis
    ]
    session.add_all(novas_associacoes)

    try:
        await session.commit()
        await session.refresh(projeto_a_editar)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar o projeto: {e}")

    # Para a resposta, recarregamos com todas as informações
    query_final = (
        select(Projeto)
        .where(Projeto.id == projeto_a_editar.id)
        .options(
            selectinload(Projeto.curso),
            selectinload(Projeto.link_professores).selectinload(ProjetoProfessor.professor)
        )
    )
    projeto_final = (await session.execute(query_final)).scalar_one()

    return projeto_final
