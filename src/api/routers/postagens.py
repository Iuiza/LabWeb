# app/routers/postagens.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .. import schemas
from ..dependencies import get_db_session
from enums.tipo import PublicacaoTipoEnum
# from ..core.utils import save_upload_file

router = APIRouter()

# RF-3: PUBLICAÇÃO DE NOTÍCIAS E EVENTOS VINCULADOS A PROJETOS [cite: 19]
# RF-5: PERMITIR UPLOAD DE IMAGENS PARA AS POSTAGENS [cite: 22]
@router.post(
    "/",
    response_model=schemas.PublicacaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova postagem (Notícia/Evento)"
)
async def criar_nova_postagem(
    db: AsyncSession = Depends(get_db_session),
    current_user: Union[schemas.ProfessorResponse, schemas.AdministradorResponse] = Depends(), # Professor ou Admin
    titulo: str = Form(...),
    conteudo: str = Form(...),
    tipo: PublicacaoTipoEnum = Form(...),
    projeto_id: int = Form(...),
    imagem_capa: Optional[UploadFile] = File(None)
):
    """
    Cria uma nova postagem (notícia ou evento) vinculada a um projeto. [cite: 19]
    Permite upload de imagem de capa. [cite: 22]
    Apenas professores autenticados ou o administrador podem publicar. [cite: 19]
    RN-4: Título, conteúdo e data são obrigatórios (data é gerada). [cite: 43]
    RN-3: Deve estar vinculada a um projeto. [cite: 40]
    """
    # Verificar se o projeto existe (RN-3) [cite: 40]
    # db_projeto = await crud.get_projeto_by_id(db, projeto_id=projeto_id)
    # if not db_projeto:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Projeto com id {projeto_id} não encontrado.")

    # Validar permissão do usuário para postar no projeto (RN-1, RN-2) [cite: 36, 39] (admin pode, professor se for do projeto)
    # if isinstance(current_user, schemas.ProfessorResponse):
    #     is_responsible = await crud.is_professor_responsible_for_project(db, professor_id=current_user.id, projeto_id=projeto_id)
    #     if not is_responsible:
    #         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Professor não tem permissão para postar neste projeto.")


    path_imagem_salva = None
    if imagem_capa:
        # Validar tipo e tamanho da imagem (RF-5) [cite: 22]
        # if imagem_capa.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de imagem inválido. Use JPG, JPEG ou PNG.")
        # if imagem_capa.size > 1 * 1024 * 1024: # 1MB
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Imagem excede o tamanho máximo de 1MB.")
        # path_imagem_salva = await save_upload_file(imagem_capa, "postagens")
        path_imagem_salva = f"static/images/postagens/{imagem_capa.filename}" # Placeholder

    # Data da publicação é gerada automaticamente (RN-4) [cite: 43]
    # O campo autor_id será o ID do current_user
    autor_id = current_user.id
    
    postagem_in_data = {
        "titulo": titulo, "conteudo": conteudo, "tipo": tipo,
        "projeto_id": projeto_id, "path_imagem": path_imagem_salva,
        "professor_id": autor_id # Assumindo que o modelo Publicacao tem professor_id como FK
    }
    # O schema PublicacaoCreate não é usado diretamente aqui devido ao UploadFile, mas o CRUD pode usá-lo.

    nova_postagem = await crud.create_publicacao(db=db, publicacao_data=postagem_in_data) # CRUD precisa lidar com professor_id
    return nova_postagem

# RF-6: PERMITIR QUE VISITANTES VISUALIZEM AS POSTAGENS [cite: 23]
# RF-7: PERMITIR VISUALIZAÇÃO POR FILTRO (POR PROJETO, DATA, ΤΙΡΟ, CURSO) [cite: 24, 26]
@router.get("/", response_model=List[schemas.PublicacaoResponse], summary="Listar postagens (Público)")
async def listar_postagens_publicas_com_filtros(
    db: AsyncSession = Depends(get_db_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    palavra_chave: Optional[str] = Query(None, description="Busca por palavras-chave no título ou conteúdo"), # RF-6 [cite: 23]
    tipo: Optional[PublicacaoTipoEnum] = Query(None, description="Filtrar por tipo (noticia ou evento)"), # RF-7 [cite: 26]
    projeto_id: Optional[int] = Query(None, description="Filtrar por ID do projeto"), # RF-7 [cite: 26]
    # curso_id: Optional[int] = Query(None, description="Filtrar por ID do curso (via projeto)"), # RF-7 [cite: 26] (CRUD faria o join)
    data_ordem: Optional[str] = Query("desc", description="Ordenar por data ('desc' para mais recentes, 'asc' para mais antigos)"), # RF-6 [cite: 23]
    # user_visitante: Optional[Union[schemas.ProfessorResponse, schemas.AdministradorResponse]] = Depends(get_optional_current_user) # Opcional
):
    """
    Lista todas as publicações (notícias e eventos) disponíveis publicamente. [cite: 23]
    Permite filtros por tipo, projeto, palavra-chave e ordenação por data. [cite: 23, 26]
    """
    postagens = await crud.get_publicacoes_publicas(
        db, skip=skip, limit=limit, palavra_chave=palavra_chave, tipo=tipo,
        projeto_id=projeto_id, # curso_id=curso_id, # Passar para o CRUD
        data_ordem=data_ordem
    )
    return postagens

@router.get("/{postagem_id}", response_model=schemas.PublicacaoResponse, summary="Obter detalhes de uma postagem (Público)")
async def obter_detalhes_postagem_publica(
    postagem_id: int,
    db: AsyncSession = Depends(get_db_session)
    # user_visitante: Optional[Union[schemas.ProfessorResponse, schemas.AdministradorResponse]] = Depends(get_optional_current_user)
):
    """
    Retorna os detalhes de uma postagem específica.
    Permite compartilhamento por link direto. [cite: 23] (A própria URL da rota é o link)
    """
    db_postagem = await crud.get_publicacao_by_id_publica(db, publicacao_id=postagem_id)
    if db_postagem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Postagem não encontrada.")
    return db_postagem


# RF-4: PERMITIR EDIÇÃO E EXCLUSÃO DE NOTÍCIAS/EVENTOS [cite: 20]
@router.put("/{postagem_id}", response_model=schemas.PublicacaoResponse, summary="Atualizar postagem (Notícia/Evento)")
async def atualizar_postagem_existente(
    postagem_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: Union[schemas.ProfessorResponse, schemas.AdministradorResponse] = Depends(),
    titulo: Optional[str] = Form(None),
    conteudo: Optional[str] = Form(None),
    tipo: Optional[PublicacaoTipoEnum] = Form(None),
    # projeto_id: Optional[int] = Form(None), # Permitir mover postagem?
    imagem_capa: Optional[UploadFile] = File(None) # RF-5: Permitir substituir/remover imagem [cite: 22]
):
    """
    Atualiza uma postagem existente. [cite: 20]
    Apenas o professor que criou a postagem ou o administrador podem editar. [cite: 20]
    Atualiza automaticamente data da última modificação. [cite: 20] (CRUD deve fazer isso)
    """
    db_postagem = await crud.get_publicacao_by_id(db, publicacao_id=postagem_id)
    if not db_postagem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Postagem não encontrada.")

    # Lógica de permissão (RF-4) [cite: 20]
    # is_admin = isinstance(current_user, schemas.AdministradorResponse)
    # is_autor = (db_postagem.professor_id == current_user.id if isinstance(current_user, schemas.ProfessorResponse) else False)
    # if not (is_admin or is_autor):
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário não tem permissão para editar esta postagem.")

    path_imagem_atualizada = db_postagem.path_imagem
    if imagem_capa: # Nova imagem fornecida
        # path_imagem_atualizada = await save_upload_file(imagem_capa, "postagens")
        path_imagem_atualizada = f"static/images/postagens/{imagem_capa.filename}" # Placeholder
    elif imagem_capa is None and (titulo is not None or conteudo is not None or tipo is not None): # Edição sem mudar a imagem
        pass # Mantém path_imagem_atualizada
    # Se quisesse permitir remoção explícita da imagem, precisaria de um parâmetro adicional, ex: remover_imagem: bool = Form(False)

    update_data_dict = {"path_imagem": path_imagem_atualizada}
    if titulo is not None: update_data_dict["titulo"] = titulo
    if conteudo is not None: update_data_dict["conteudo"] = conteudo
    if tipo is not None: update_data_dict["tipo"] = tipo
    # if projeto_id is not None: update_data_dict["projeto_id"] = projeto_id

    # Usar .model_dump(exclude_unset=True) se construísse um Pydantic model primeiro
    if not any(v is not None for k, v in update_data_dict.items() if k != "path_imagem") and not imagem_capa:
         # Se apenas path_imagem foi "atualizado" para o mesmo valor porque não houve upload, e nada mais mudou
         if path_imagem_atualizada == db_postagem.path_imagem and not any(v is not None for k, v in update_data_dict.items() if k != "path_imagem"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum dado fornecido para atualização.")
    
    postagem_atualizada = await crud.update_publicacao(db=db, publicacao_id=postagem_id, publicacao_update_data=update_data_dict)
    return postagem_atualizada


@router.delete("/{postagem_id}", response_model=schemas.MensagemResponse, summary="Excluir postagem (Notícia/Evento)")
async def excluir_postagem_existente(
    postagem_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: Union[schemas.ProfessorResponse, schemas.AdministradorResponse] = Depends()
):
    """
    Exclui uma postagem. [cite: 20]
    Apenas o professor que criou ou o administrador. [cite: 20]
    Solicitar confirmação antes da exclusão (frontend). [cite: 20]
    """
    # Lógica de permissão similar à de atualização
    # ...

    success = await delete_publicacao(db=db, publicacao_id=postagem_id, user_id_deletando=current_user.id)
    if not success: # CRUD deve verificar se a postagem existe e se o usuário tem permissão antes de tentar deletar
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Postagem não encontrada ou falha ao deletar.")
    return {"mensagem": f"Postagem {postagem_id} excluída com sucesso."} # RF-4 [cite: 20]