from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import select

from .. import schemas, security
from ..dependencies import get_db_session, get_current_admin_user
from models.db import Professor, Administrador
from ..email_service import enviar_email_acesso

router = APIRouter()

# ROTA PARA ADMINISTRADOR CRIAR NOVO PROFESSOR
@router.post(
    "/cadastrar",
    response_model=schemas.ProfessorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar um novo professor (Admin)"
)
async def cadastrar_professor(
    dados_professor: schemas.ProfessorCreate,
    admin: Administrador = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Permite que um administrador cadastre um novo professor no sistema. [cite: 81]
    A senha fornecida é hasheada antes de ser salva. [cite: 107]
    Um e-mail com os dados de acesso é enviado ao professor. [cite: 82]
    """
    # Verifica se o email ou CPF já existem
    query = select(Professor).where((Professor.email == dados_professor.email) | (Professor.cpf == dados_professor.cpf))
    if (await session.execute(query)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email ou CPF já cadastrado.")

    # Hashear a senha antes de salvar
    senha_hasheada = security.hash_password(dados_professor.senha)

    novo_professor = Professor(
        nome=dados_professor.nome,
        email=dados_professor.email,
        cpf=dados_professor.cpf,
        senha=senha_hasheada
    )
    session.add(novo_professor)

    await session.commit()
    await session.refresh(novo_professor)

    # Envia o email com a senha original (não hasheada)
    await enviar_email_acesso(email_destinatario=novo_professor.email, senha=dados_professor.senha)
    
    return novo_professor

# ROTA PARA ADMINISTRADOR EDITAR PROFESSOR
@router.put(
    "/editar/{professor_id}",
    response_model=schemas.ProfessorResponse,
    summary="Editar um professor (Admin)"
)
async def editar_professor(
    professor_id: int,
    dados_edicao: schemas.ProfessorUpdate,
    admin: Administrador = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Permite que um administrador edite as informações de um professor. [cite: 100]
    """
    professor = await session.get(Professor, professor_id)
    if not professor:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")

    # Atualiza os dados fornecidos (ignora os que forem None)
    update_data = dados_edicao.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(professor, key, value)
    
    session.add(professor)
    await session.commit()
    await session.refresh(professor)
    
    return professor

# ROTA PARA REENVIAR EMAIL DE ACESSO (SEM ALTERAR SENHA)
@router.post(
    "/{professor_id}/reenviar-acesso",
    status_code=status.HTTP_200_OK,
    summary="Reenviar e-mail de acesso (Admin)"
)
async def reenviar_acesso_professor(
    professor_id: int,
    admin: Administrador = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Gera uma NOVA senha temporária e a envia por e-mail para o professor. [cite: 100]
    Isto é mais seguro do que reenviar uma senha antiga.
    """
    professor = await session.get(Professor, professor_id)
    if not professor:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")

    # Gera uma nova senha temporária (ex: 8 caracteres aleatórios)
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    nova_senha_temporaria = ''.join(secrets.choice(alphabet) for i in range(8))
    
    # Atualiza o hash da senha no banco
    professor.senha = security.hash_password(nova_senha_temporaria)
    session.add(professor)
    await session.commit()

    # Envia o e-mail com a NOVA senha
    await enviar_email_acesso(email_destinatario=professor.email, senha=nova_senha_temporaria)
    
    return {"detail": f"Um e-mail com uma nova senha de acesso foi enviado para {professor.email}."}
