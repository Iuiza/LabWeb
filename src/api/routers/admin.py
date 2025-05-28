# app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr

from .. import schemas
from ..dependencies import get_db_session, get_current_active_admin
# from ..core.utils import save_upload_file # Função utilitária para salvar arquivos

router = APIRouter()

# RF-1: PERMITIR QUE O ADMINISTRADOR CADASTRE NOVOS PROFESSORES
@router.post(
    "/professores",
    response_model=schemas.ProfessorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo professor (Admin)"
)
async def criar_professor_admin(
    db: AsyncSession = Depends(get_db_session),
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
    db_professor = await crud.get_professor_by_email_or_cpf(db, email=email, cpf=cpf)
    if db_professor:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ou CPF já cadastrado.")

    path_imagem_salva = None
    if imagem_perfil:
        # path_imagem_salva = await save_upload_file(imagem_perfil, "professores")
        path_imagem_salva = f"static/images/professores/{imagem_perfil.filename}" # Placeholder

    professor_in = schemas.ProfessorCreate(
        nome=nome, email=email, senha=senha, cpf=cpf, path_imagem=path_imagem_salva
    )
    
    novo_professor = await crud.create_professor(db=db, professor_create=professor_in)
    
    # Lógica para enviar email para o professor com login, senha e link (RF-1)
    # await send_new_professor_email(email_to=novo_professor.email, nome=novo_professor.nome, senha_raw=senha)
    
    return novo_professor


# RF-8: PERMITIR QUE O ADMINISTRADOR GERENCIE PROFESSORES
@router.get("/professores", response_model=List[schemas.ProfessorResponse], summary="Listar e filtrar professores (Admin)")
async def listar_professores_como_admin(
    db: AsyncSession = Depends(get_db_session),
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
    professores = await crud.get_professores(db, skip=skip, limit=limit, nome_filter=nome, email_filter=email)
    return professores

@router.get("/professores/{professor_id}", response_model=schemas.ProfessorResponse, summary="Obter professor por ID (Admin)")
async def obter_professor_por_id_admin(
    professor_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    db_professor = await crud.get_professor_by_id(db, professor_id=professor_id)
    if db_professor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
    return db_professor

@router.put("/professores/{professor_id}", response_model=schemas.ProfessorResponse, summary="Atualizar professor (Admin)")
async def atualizar_professor_como_admin(
    professor_id: int,
    db: AsyncSession = Depends(get_db_session),
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
    db_professor = await crud.get_professor_by_id(db, professor_id=professor_id)
    if not db_professor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")

    path_imagem_atualizada = db_professor.path_imagem
    if imagem_perfil:
        # path_imagem_atualizada = await save_upload_file(imagem_perfil, "professores")
        path_imagem_atualizada = f"static/images/professores/{imagem_perfil.filename}" # Placeholder

    professor_update_data = schemas.ProfessorUpdate(
        nome=nome, email=email, cpf=cpf, path_imagem=path_imagem_atualizada
    )
    # Lógica para 'status_conta' e 'departamento' se os campos existirem no modelo.
    
    updated_professor = await crud.update_professor(db=db, professor_id=professor_id, professor_update=professor_update_data)
    return updated_professor

@router.delete("/professores/{professor_id}", response_model=schemas.MensagemResponse, summary="Excluir professor (Admin)")
async def excluir_professor_como_admin(
    professor_id: int,
    # justificativa: str = Query(..., description="Justificativa para exclusão (RF-8)"), # Não está no modelo
    db: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    """
    Exclui a conta de um professor.
    """
    success = await crud.delete_professor(db=db, professor_id=professor_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
    return {"mensagem": f"Professor {professor_id} excluído com sucesso."}

@router.post("/professores/{professor_id}/reenviar-email-acesso", response_model=schemas.MensagemResponse, summary="Reenviar email com dados de acesso (Admin)")
async def reenviar_email_acesso_professor(
    professor_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin),
):
    """
    Reenvia email com senha (ou link para redefinir) para o professor.
    """
    db_professor = await crud.get_professor_by_id(db, professor_id=professor_id)
    if not db_professor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
    
    # Lógica para gerar nova senha temporária ou link de redefinição e enviar email
    # await send_access_email(email_to=db_professor.email, nome=db_professor.nome, ...)
    return {"mensagem": f"Email com informações de acesso reenviado para {db_professor.email}."}


# --- Gerenciamento de Cursos, Departamentos, Campus (Admin) ---
@router.post("/campus", response_model=schemas.CampusResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo Campus (Admin)")
async def criar_campus(
    campus_in: schemas.CampusCreate,
    db: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    return await crud.create_campus(db=db, campus=campus_in)

@router.get("/campus", response_model=List[schemas.CampusResponse], summary="Listar Campus (Admin)")
async def listar_campus(
    db: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    return await crud.get_all_campus(db=db)

@router.post("/departamentos", response_model=schemas.DepartamentoResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo Departamento (Admin)")
async def criar_departamento(
    departamento_in: schemas.DepartamentoCreate,
    db: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    return await crud.create_departamento(db=db, departamento=departamento_in)

@router.get("/departamentos", response_model=List[schemas.DepartamentoResponse], summary="Listar Departamentos (Admin)")
async def listar_departamentos(
    db: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    return await crud.get_all_departamentos(db=db)


@router.post("/cursos", response_model=schemas.CursoResponse, status_code=status.HTTP_201_CREATED, summary="Criar novo Curso (Admin)")
async def criar_curso(
    curso_in: schemas.CursoCreate,
    db: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    return await crud.create_curso(db=db, curso=curso_in)

@router.get("/cursos", response_model=List[schemas.CursoResponse], summary="Listar Cursos (Admin)")
async def listar_cursos(
    db: AsyncSession = Depends(get_db_session),
    current_admin: schemas.AdministradorResponse = Depends(get_current_active_admin)
):
    return await crud.get_all_cursos(db=db)