from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from enums.status import ProjetoStatusEnum
from enums.tipo import PublicacaoTipoEnum

# ---- Autenticação ----
class Token(BaseModel):
    access_token: str
    token_type: str

class PasswordChange(BaseModel):
    senha_antiga: str
    senha_nova: str

# ---- Campus ----
class CampusBase(BaseModel):
    nome: str

class CampusCreate(CampusBase):
    pass

class CampusResponse(CampusBase):
    id: int

    class Config:
        from_attributes = True

# ---- Departamento ----
class DepartamentoBase(BaseModel):
    nome: str
    campus_id: int

class DepartamentoCreate(DepartamentoBase):
    pass

class DepartamentoResponse(DepartamentoBase):
    id: int
    campus: CampusResponse

    class Config:
        from_attributes = True

# ---- Curso ----
class CursoBase(BaseModel):
    nome: str
    departamento_id: int

class CursoCreate(CursoBase):
    pass

class CursoResponse(CursoBase):
    id: int
    departamento: DepartamentoResponse

    class Config:
        from_attributes = True

class CursoSimplificado(BaseModel):
    id: int
    nome: str
    class Config:
        from_attributes = True
        
# ---- Professor ----
class ProfessorBase(BaseModel):
    nome: str
    email: EmailStr

class ProfessorCreate(ProfessorBase):
    senha: str
    cpf: str

class ProfessorUpdate(BaseModel):
    nome: str | None = None
    email: EmailStr | None = None

class ProfessorResponse(ProfessorBase):
    id: int
    path_imagem: str | None = None

    class Config:
        from_attributes = True

class ProfessorSimplificado(ProfessorBase):
    id: int

    class Config:
        from_attributes = True

# ---- Publicação (Schemas Simplificados para uso em outras respostas) ----
class PublicacaoSimplificado(BaseModel):
    id: int
    titulo: str

    class Config:
        from_attributes = True

# ---- Projeto ----
class ProjetoBase(BaseModel):
    titulo: str = Field(..., min_length=3)
    descricao: Optional[str] = None
    path_imagem: Optional[str] = None
    data_inicio: datetime
    data_fim: Optional[datetime] = None
    status: ProjetoStatusEnum = ProjetoStatusEnum.ATIVO
    publico: str
    curso_id: int

class ProjetoSimplesResponse(BaseModel):
    id: int
    titulo: str

    class Config:
        from_attributes = True

class ProjetoResponse(ProjetoBase):
    id: int
    curso: CursoResponse 
    professores: List[ProfessorSimplificado] = []
    publicacoes: List[PublicacaoSimplificado] = []
    
    class Config:
        from_attributes = True

# ---- Publicação (Schemas Completos) ----
class PublicacaoBase(BaseModel):
    titulo: str
    tipo: PublicacaoTipoEnum
    data_publicacao: datetime

class PublicacaoResponse(PublicacaoBase):
    id: int
    conteudo: str
    path_imagem: str | None = None
    professor: ProfessorResponse
    projeto: ProjetoSimplesResponse

    class Config:
        from_attributes = True

class PaginatedPublicacaoResponse(BaseModel):
    total: int
    publicacoes: List[PublicacaoResponse]