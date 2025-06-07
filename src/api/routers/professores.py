# app/routers/professores.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas
from ..dependencies import get_db_session, get_current_active_professor

router = APIRouter()

@router.get("/me", response_model=schemas.ProfessorResponse, summary="Obter dados do professor logado")
async def ler_dados_professor_logado(
    current_professor: schemas.ProfessorResponse = Depends(get_current_active_professor)
):
    """
    Retorna os dados do professor atualmente autenticado.
    """
    return current_professor

@router.put("/me/alterar-senha", response_model=schemas.MensagemResponse, summary="Alterar senha do professor logado")
async def alterar_senha_do_professor_logado(
    payload: schemas.PasswordChangeSchema,
    db: AsyncSession = Depends(get_db_session),
    current_professor: schemas.ProfessorResponse = Depends(get_current_active_professor)
):
    """
    Permite que o professor logado altere sua própria senha. [cite: 15]
    """
    success = await update_professor_password(
        db=db,
        professor_id=current_professor.id,
        senha_atual=payload.senha_atual,
        nova_senha=payload.nova_senha
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta ou erro ao atualizar.")
    return {"mensagem": "Senha alterada com sucesso."}

# Outras rotas específicas para professores (ex: listar SEUS projetos com edição)
# podem ser adicionadas aqui ou nas rotas de `projetos.py` com verificação de permissão.