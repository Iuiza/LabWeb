# app/dependencies.py
from typing import AsyncGenerator, Optional, Union
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Supondo que database.py e schemas.py estão no mesmo nível ou acessíveis
from models.db import LocalAsyncSession
from . import schemas
# from .core.security import oauth2_scheme, decode_access_token # Sua implementação de segurança

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with LocalAsyncSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# --- Placeholders de Autenticação ---
# Implemente sua lógica real de autenticação aqui

async def get_current_user_base(
    # token: str = Depends(oauth2_scheme), # Sua implementação real
    db: AsyncSession = Depends(get_db_session)
) -> Union[schemas.ProfessorResponse, schemas.AdministradorResponse]: # Union type
    # Placeholder: Em um sistema real, decodifique o token, busque o usuário no DB
    # email = decode_access_token(token)
    # user = await crud.get_user_by_email(db, email=email) # Função CRUD genérica
    # if not user:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    # return user # Retorna o objeto do usuário (Professor ou Admin)
    print(f"Placeholder: get_current_user_base com sessão DB: {db}")
    # Simular um tipo de usuário para teste, você precisaria de uma lógica para diferenciar
    # Por exemplo, verificando um campo 'role' no token ou no modelo do usuário.
    # Aqui, vamos simular um professor para rotas que podem ser acessadas por ambos logados.
    user_simulado = await get_professor_by_id(db, professor_id=1) # Assumindo que existe um prof com ID 1 ou mock
    if user_simulado:
        return user_simulado
    # Ou simular um admin
    # admin_simulado = await crud.get_admin_by_id(db, admin_id=1)
    # if admin_simulado: return admin_simulado

    # Fallback se o crud não retornar nada (para o placeholder funcionar sem DB real)
    return schemas.ProfessorResponse(id=99, nome="Usuário Mock", email="user@example.com", cpf="00000000000")


async def get_current_active_professor(
    current_user: schemas.ProfessorResponse = Depends(get_current_user_base)
) -> schemas.ProfessorResponse:
    if not isinstance(current_user, schemas.ProfessorResponse): # Verifique o tipo real do usuário
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a professores")
    # if not current_user.is_active: # Se tiver campo is_active no modelo Professor
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_admin(
    current_user: schemas.AdministradorResponse = Depends(get_current_user_base)
) -> schemas.AdministradorResponse:
    # No seu modelo Administrador não há 'is_active', mas a lógica de permissão é importante
    if not isinstance(current_user, schemas.AdministradorResponse): # Verifique o tipo real do usuário
         # Se get_current_user_base retorna um tipo Union, você precisa de um admin específico aqui.
         # Esta é uma simplificação; você precisaria de uma forma de obter APENAS admin.
         # Por exemplo, get_current_user_base poderia retornar um objeto com um campo 'role'.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return current_user

# Para visitantes (usuário opcional)
async def get_optional_current_user(
    # token: Optional[str] = Depends(oauth2_scheme_optional), # Uma dependência opcional de token
    db: AsyncSession = Depends(get_db_session)
) -> Optional[Union[schemas.ProfessorResponse, schemas.AdministradorResponse]]:
    # if not token:
    #     return None
    # try:
    #     email = decode_access_token(token)
    #     user = await crud.get_user_by_email(db, email=email)
    #     return user
    # except HTTPException: # Se o token for inválido mas opcional, não levanta erro
    #     return None
    print(f"Placeholder: get_optional_current_user com sessão DB: {db}")
    return None