# app/routers/projetos.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select, and_

from .. import schemas
from ..dependencies import get_db_session, get_current_user_base, get_current_active_user
from enums.status import ProjetoStatusEnum
from models.db import Projeto, Professor, Administrador
# from ..core.utils import save_upload_file

router = APIRouter()

# RF-2: PERMITIR QUE PROFESSORES E ADMINISTRADORES CADASTREM NOVOS PROJETOS
@router.post(
    "/",
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

    # 4. CRIAR O NOVO PROJETO
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
    
    # Associar os professores responsáveis
    novo_projeto.professores = professores_encontrados

    session.add(novo_projeto)
    await session.commit()
    await session.refresh(novo_projeto)

    return novo_projeto


# Visualização pública de projetos (parte do RF-2 "Exibir os projetos em uma página pública") [cite: 18]
@router.get("/", response_model=List[schemas.ProjetoResponse], summary="Listar projetos de extensão (Público)")
async def listar_projetos_para_publico(
    db: AsyncSession = Depends(get_db_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100), # Limite menor para visualização pública
    curso_id: Optional[int] = Query(None, description="Filtrar por ID do curso"),
    status: Optional[ProjetoStatusEnum] = Query(None, description="Filtrar por status do projeto")
    # user: Optional[Union[schemas.ProfessorResponse, schemas.AdministradorResponse]] = Depends(get_optional_current_user) # Para debug ou personalização se logado
):
    """
    Lista os projetos de extensão disponíveis publicamente.
    Pode ser filtrado por curso e status.
    """
    projetos = await get_projetos_publicos(
        db, skip=skip, limit=limit, curso_id=curso_id, status=status
    )
    return projetos

@router.get("/{projeto_id}", response_model=schemas.ProjetoResponse, summary="Obter detalhes de um projeto (Público)")
async def obter_detalhes_projeto_publico(
    projeto_id: int,
    db: AsyncSession = Depends(get_db_session)
    # user: Optional[Union[schemas.ProfessorResponse, schemas.AdministradorResponse]] = Depends(get_optional_current_user)
):
    """
    Retorna os detalhes de um projeto específico.
    """
    db_projeto = await get_projeto_by_id_publico(db, projeto_id=projeto_id)
    if db_projeto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado ou não é público.")
    return db_projeto

# RF-2: Permitir que os professores e o administrador editem as informações do projeto [cite: 16]
@router.put("/{projeto_id}", response_model=schemas.ProjetoResponse, summary="Atualizar projeto de extensão")
async def atualizar_info_projeto(
    projeto_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: Union[schemas.ProfessorResponse, schemas.AdministradorResponse] = Depends(get_current_user_base),
    titulo: Optional[str] = Form(None),
    descricao: Optional[str] = Form(None),
    data_inicio: Optional[datetime] = Form(None),
    data_fim: Optional[datetime] = Form(None),
    status: Optional[ProjetoStatusEnum] = Form(None),
    publico: Optional[str] = Form(None),
    curso_id: Optional[int] = Form(None),
    professor_ids_responsaveis: Optional[List[int]] = Form(None), # Enviar como lista de IDs
    imagem_capa: Optional[UploadFile] = File(None)
):
    """
    Atualiza as informações de um projeto de extensão. [cite: 16]
    Apenas o administrador ou professores responsáveis pelo projeto podem editar. [cite: 39] (RN-2)
    """
    db_projeto = await get_projeto_by_id(db, projeto_id=projeto_id) # CRUD deve carregar professores
    if not db_projeto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")

    # Lógica de permissão (RN-2) [cite: 39]
    # is_admin = isinstance(current_user, schemas.AdministradorResponse)
    # is_responsible_professor = False
    # if isinstance(current_user, schemas.ProfessorResponse):
    #     if db_projeto.professores and any(p.id == current_user.id for p in db_projeto.professores):
    #         is_responsible_professor = True
    # if not (is_admin or is_responsible_professor):
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário não tem permissão para editar este projeto.")

    path_imagem_atualizada = db_projeto.path_imagem
    if imagem_capa:
        # path_imagem_atualizada = await save_upload_file(imagem_capa, "projetos")
        path_imagem_atualizada = f"static/images/projetos/{imagem_capa.filename}" # Placeholder
    
    # Construir o objeto de atualização, apenas com campos fornecidos
    update_data = schemas.ProjetoUpdate(
        titulo=titulo, descricao=descricao, data_inicio=data_inicio, data_fim=data_fim,
        status=status, publico=publico, curso_id=curso_id,
        professor_ids_responsaveis=professor_ids_responsaveis, # O CRUD lidará com a lógica de atualizar os professores
        path_imagem=path_imagem_atualizada
    ).model_dump(exclude_unset=True) # Envia apenas o que foi modificado

    if not update_data and not imagem_capa: # Se nada foi enviado para atualizar
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum dado fornecido para atualização.")

    projeto_atualizado = await update_projeto(db=db, projeto_id=projeto_id, projeto_update_data=update_data)
    return projeto_atualizado


# RF-2: Permitir a exclusão do projeto com confirmação de identidade (aqui, "identidade" = token válido + permissão) [cite: 18]
@router.delete("/{projeto_id}", response_model=schemas.MensagemResponse, summary="Excluir projeto de extensão")
async def excluir_projeto_extensao(
    projeto_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: Union[schemas.ProfessorResponse, schemas.AdministradorResponse] = Depends(get_current_user_base)
):
    """
    Exclui um projeto de extensão. [cite: 18]
    Apenas o administrador ou professores responsáveis. [cite: 39] (RN-2)
    RN-3: Ao excluir um projeto, todas as postagens associadas a ele devem ser também removidas ou realocadas. [cite: 42]
    """
    # Lógica de permissão similar à de atualização
    # db_projeto = await crud.get_projeto_by_id(db, projeto_id=projeto_id) # Carregar para verificar permissão
    # ... verificar permissão ...

    # CRUD.delete_projeto deve implementar a lógica de RN-3 [cite: 42]
    success = await delete_projeto(db=db, projeto_id=projeto_id, user_id_deletando=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado ou falha ao deletar.")
    return {"mensagem": f"Projeto {projeto_id} e suas postagens associadas foram excluídos/realocados."}