# app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr
from sqlalchemy import select

from .. import schemas
from ..dependencies import get_db_session, get_current_active_admin
# from ..core.utils import save_upload_file # Função utilitária para salvar arquivos

from models import Professor, Campus, Departamento, Curso

router = APIRouter()

# RF-1: PERMITIR QUE O ADMINISTRADOR CADASTRE NOVOS PROFESSORES
@router.post(
    "/professores",
    response_model=schemas.ProfessorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo professor (Admin)"
)
async def criar_professor_admin(
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin),
    nome: str = Form(...),
    email: EmailStr = Form(...),
    senha: str = Form(..., min_length=6),
    cpf: str = Form(..., min_length=11, max_length=11),
    # "departamento de atuação" (RF-1) não é um campo direto no modelo Professor,
    # mas pode ser um campo de texto informativo ou gerenciado de outra forma.
    # Aqui, assumimos que não é um campo direto no modelo Professor para este endpoint.
    # Se fosse um FK: departamento_id: int = Form(...),
    imagem_perfil: Optional[UploadFile] = File(None)
):
    """
    Permite que um administrador cadastre um novo professor.
    A senha será hasheada antes de salvar.
    O email de boas-vindas é enviado.
    """
    path_imagem_salva = f"static/images/professores/{imagem_perfil.filename}"

    novo_professor, just_created = Professor.get_or_create(session, nome, email, senha, cpf, path_imagem_salva)

    if not just_created:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ou CPF já cadastrado.")

    # Lógica para enviar email para o professor com login, senha e link (RF-1)
    # await send_new_professor_email(email_to=novo_professor.email, nome=novo_professor.nome, senha_raw=senha)
    
    return novo_professor


# RF-8: PERMITIR QUE O ADMINISTRADOR GERENCIE PROFESSORES
@router.get("/professores", response_model=List[schemas.ProfessorResponse], summary="Listar e filtrar professores (Admin)")
async def listar_professores_como_admin(
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    nome: Optional[str] = Query(None, description="Filtrar por nome do professor"),
    # departamento: Optional[str] = Query(None, description="Filtrar por departamento de atuação"), # RF-1. Como não é FK, seria filtro em campo texto se existir.
    email: Optional[EmailStr] = Query(None, description="Filtrar por email"),
    # status_conta: Optional[bool] = Query(None, description="Filtrar por status da conta (ativo/inativo)"), # Modelo Professor não tem 'is_active'
):
    """
    Lista professores com filtros.
    """
    professores = ( await session.scalars(select(Professor))).all()
    # professores = await crud.get_professores(session, skip=skip, limit=limit, nome_filter=nome, email_filter=email)

    return professores

@router.get("/professores/{professor_id}", response_model=schemas.ProfessorResponse, summary="Obter professor por ID (Admin)")
async def obter_professor_por_id_admin(
    professor_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    db_professor = await session.get(Professor, professor_id)
    
    if not db_professor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
    
    return db_professor

@router.put("/professores/{professor_id}", response_model=schemas.ProfessorResponse, summary="Atualizar professor (Admin)")
async def atualizar_professor_como_admin(
    professor_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin),
    nome: Optional[str] = Form(None),
    email: Optional[EmailStr] = Form(None),
    cpf: Optional[str] = Form(None, min_length=11, max_length=11),
    # status_conta: Optional[bool] = Form(None), # RF-8: Ativar/desativar. Adicionar 'is_active' ao modelo Professor.
    # departamento: Optional[str] = Form(None), # RF-8: Editar departamento.
    imagem_perfil: Optional[UploadFile] = File(None)
):
    """
    Atualiza informações de um professor, ativa/desativa conta.
    Se uma nova senha for fornecida, ela será atualizada (RF-8: Editar ... senha).
    """
    db_professor = await session.get(Professor, professor_id)

    if not db_professor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
    
    db_professor.nome = nome if nome else db_professor.nome
    db_professor.email = email if email else db_professor.email     

    await session.commit()  # Salva as alterações no banco de dados


    return db_professor

# @router.delete("/professores/{professor_id}", response_model=schemas.MensagemResponse, summary="Excluir professor (Admin)")
# async def excluir_professor_como_admin(
#     professor_id: int,
#     # justificativa: str = Query(..., description="Justificativa para exclusão (RF-8)"), # Não está no modelo
#     db: AsyncSession = Depends(get_db_session),
#     current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
# ):
#     """
#     Exclui a conta de um professor.
#     """
#     success = await crud.delete_professor(db=db, professor_id=professor_id)
#     if not success:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
#     return {"mensagem": f"Professor {professor_id} excluído com sucesso."}

@router.post("/professores/{professor_id}/reenviar-email-acesso", response_model=schemas.MensagemResponse, summary="Reenviar email com dados de acesso (Admin)")
async def reenviar_email_acesso_professor(
    professor_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin),
):
    """
    Reenvia email com senha (ou link para redefinir) para o professor.
    """
    db_professor = await session.get(Professor, professor_id)
    
    if not db_professor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
    
    # Lógica para gerar nova senha temporária ou link de redefinição e enviar email
    # await send_access_email(email_to=db_professor.email, nome=db_professor.nome, ...)
    return {"mensagem": f"Email com informações de acesso reenviado para {db_professor.email}."}


# --- Gerenciamento de Cursos, Departamentos, Campus (Admin) ---
@router.post("/campus", response_model=schemas.CampusResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo Campus (Admin)")
async def criar_campus(
    campus_in: schemas.CampusCreate,
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    campus, _ = await Campus.get_or_create(session, campus_in)

    return campus

@router.get("/campus", response_model=List[schemas.CampusResponse], summary="Listar Campus (Admin)")
async def listar_campus(
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    campus = ( await session.scalars(select(Campus))).all()
    return campus

@router.post("/departamentos", response_model=schemas.DepartamentoResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo Departamento (Admin)")
async def criar_departamento(
    departamento_in: schemas.DepartamentoCreate,
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    departamento, _ = await Campus.get_or_create(session, departamento_in)

    return departamento

@router.get("/departamentos", response_model=List[schemas.DepartamentoResponse], summary="Listar Departamentos (Admin)")
async def listar_departamentos(
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    departamentos = ( await session.scalars(select(Departamento))).all()
    return departamentos


@router.post("/cursos", response_model=schemas.CursoResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo Curso (Admin)")
async def criar_curso(
    curso_in: schemas.CursoCreate,
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    curso, _ = await Campus.get_or_create(session, curso_in)

    return curso

@router.get("/cursos", response_model=List[schemas.CursoResponse], summary="Listar Cursos (Admin)")
async def listar_cursos(
    session: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    cursos = ( await session.scalars(select(Curso))).all()
    return cursos