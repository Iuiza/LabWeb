# app/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime # SQLAlchemy usa datetime para timestamp e datetime_default_now
from enums.status import ProjetoStatusEnum
from enums.tipo import PublicacaoTipoEnum # Importe seus enums

# ---- Base e Respostas Simplificadas (para evitar recursão em listas) ----
class ProfessorSimplificado(BaseModel):
    id: int
    nome: str
    email: EmailStr

    class Config:
        from_attributes = True

class ProjetoSimplificado(BaseModel):
    id: int
    titulo: str

    class Config:
        from_attributes = True

class CursoSimplificado(BaseModel):
    id: int
    nome: str
    class Config:
        from_attributes = True

class DepartamentoSimplificado(BaseModel):
    id: int
    nome: str
    class Config:
        from_attributes = True

class CampusSimplificado(BaseModel):
    id: int
    nome: str
    class Config:
        from_attributes = True


# ---- Professor ----
class ProfessorBase(BaseModel):
    nome: str = Field(..., min_length=3)
    email: EmailStr
    cpf: str = Field(..., min_length=11, max_length=11)
    path_imagem: Optional[str] = None

class ProfessorCreate(ProfessorBase):
    senha: str = Field(..., min_length=6)
    # "departamento de atuação" (RF-1) não é um campo direto no seu modelo Professor.
    # Se precisar ser armazenado, o modelo Professor precisaria de um campo ou relação.
    # Por agora, ele não está aqui.

class ProfessorUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3)
    email: Optional[EmailStr] = None
    path_imagem: Optional[str] = None
    cpf: Optional[str] = Field(None, min_length=11, max_length=11)
    # Não permitir atualização de senha aqui, usar rota específica

class ProfessorResponse(ProfessorBase):
    id: int
    # Para exibir em respostas, podemos escolher não incluir projetos/publicações
    # ou usar modelos simplificados para evitar dados excessivos e recursão.
    # projetos: List[ProjetoSimplificado] = []
    # publicacoes: List[PublicacaoSimplificado] = [] # Definir PublicacaoSimplificado

    class Config:
        from_attributes = True # Anteriormente orm_mode

# ---- Administrador ----
class AdministradorBase(BaseModel):
    nome: str
    email: EmailStr

class AdministradorCreate(AdministradorBase):
    senha: str

class AdministradorResponse(AdministradorBase):
    id: int
    class Config:
        from_attributes = True

# ---- Autenticação ----
class LoginSchema(BaseModel):
    email: EmailStr
    senha: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None # 'professor', 'admin'

class PasswordChangeSchema(BaseModel):
    senha_atual: str
    nova_senha: str

# ---- Campus ----
class CampusBase(BaseModel):
    nome: str

class CampusCreate(CampusBase):
    pass

class CampusResponse(CampusBase):
    id: int
    # departamentos: List[DepartamentoSimplificado] = [] # Opcional
    class Config:
        from_attributes = True

# ---- Departamento ----
class DepartamentoBase(BaseModel):
    nome: str
    # campus_id: int # Se for criar/linkar via ID

class DepartamentoCreate(DepartamentoBase):
    campus_id: int # Para vincular ao criar

class DepartamentoResponse(DepartamentoBase):
    id: int
    campus: CampusSimplificado # Opcional, se quiser mostrar o campus vinculado
    # cursos: List[CursoSimplificado] = [] # Opcional
    class Config:
        from_attributes = True

# ---- Curso ----
class CursoBase(BaseModel):
    nome: str
    # departamento_id: int # Se for criar/linkar via ID

class CursoCreate(CursoBase):
    departamento_id: int # Para vincular ao criar

class CursoResponse(CursoBase):
    id: int
    departamento: DepartamentoSimplificado # Opcional
    # projetos: List[ProjetoSimplificado] = [] # Opcional
    class Config:
        from_attributes = True

# ---- Projeto ----
class ProjetoBase(BaseModel):
    titulo: str = Field(..., min_length=3)
    descricao: Optional[str] = None
    path_imagem: Optional[str] = None # Opcional na criação, pode ser atualizado depois
    data_inicio: datetime # SQLAlchemy timestamp é Python datetime
    data_fim: Optional[datetime] = None
    status: ProjetoStatusEnum = ProjetoStatusEnum.ATIVO
    publico: str # Definir melhor o que "publico" significa. Se for boolean, use bool.
    curso_id: int # FK para Curso

class ProjetoCreate(ProjetoBase):
    # `professores_ids` seria usado pela lógica da rota para criar os links
    # na tabela de associação se você tiver uma relação many-to-many explícita
    # ou para adicionar à lista `professores` se for many-to-many implícita do SQLAlchemy.
    # Seus modelos atuais sugerem uma relação many-to-many implícita via back_populates.
    # A forma de lidar com isso no CRUD dependerá de como você gerencia a sessão e os objetos.
    # Para simplicidade, podemos passar os IDs e o CRUD lida com o fetch e append.
    professor_ids_responsaveis: List[int] = []


class ProjetoUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3)
    descricao: Optional[str] = None
    path_imagem: Optional[str] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    status: Optional[ProjetoStatusEnum] = None
    publico: Optional[str] = None
    curso_id: Optional[int] = None
    professor_ids_responsaveis: Optional[List[int]] = None

class ProjetoResponse(ProjetoBase):
    id: int
    curso: CursoSimplificado # Mostra o curso vinculado
    professores: List[ProfessorSimplificado] = [] # Mostra os professores vinculados
    # publicacoes: List[PublicacaoSimplificado] = [] # Opcional
    class Config:
        from_attributes = True

# ---- Publicacao (Notícia/Evento) ----
class PublicacaoBase(BaseModel):
    titulo: str = Field(..., min_length=3)
    conteudo: str # Seu modelo usa longtext
    tipo: PublicacaoTipoEnum
    # path_imagem é 'timestamp' no seu modelo Publicacao, isso parece um erro.
    # Deveria ser uma string para o caminho do arquivo, como nos outros. Vou assumir str.
    path_imagem: Optional[str] = None # Opcional na criação
    projeto_id: int # FK para Projeto
    # professor_id será o autor, pego do usuário logado na rota de criação

class PublicacaoCreate(BaseModel): # Schema específico para criação via form-data
    titulo: str = Field(..., min_length=3)
    conteudo: str
    tipo: PublicacaoTipoEnum
    projeto_id: int
    # A imagem e o professor_id (autor) serão tratados na rota

class PublicacaoUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3)
    conteudo: Optional[str] = None
    tipo: Optional[PublicacaoTipoEnum] = None
    path_imagem: Optional[str] = None
    # Mover para outro projeto?
    # projeto_id: Optional[int] = None

class PublicacaoResponse(PublicacaoBase):
    id: int
    data_publicacao: datetime # Vem do datetime_default_now
    # Seu modelo não tem 'data_ultima_modificacao', pode ser adicionado se necessário
    professor: ProfessorSimplificado # Autor da publicação
    projeto: ProjetoSimplificado # Projeto vinculado
    class Config:
        from_attributes = True

class MensagemResponse(BaseModel):
    mensagem: str