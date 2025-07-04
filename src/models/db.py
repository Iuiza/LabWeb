import asyncio

from typing import Annotated, cast
from urllib.parse import quote
from sqlalchemy import (
    Engine,
    create_engine,
    ForeignKey,
    select,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy.orm import (
    relationship,
    mapped_column,
    Mapped,
    sessionmaker,
    DeclarativeBase,
    Session,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from config import settings
from enums.status import ProjetoStatusEnum
from enums.tipo import PublicacaoTipoEnum
from models.db_annotations import (
    text,
    timestamp,
    datetime_default_now,
    longtext,
    big_intpk,
)


engine = cast(Engine, None)

async_engine = cast(AsyncEngine, None)

__async_session = cast(async_sessionmaker, None)

__session = cast(sessionmaker, None)


def setup_db():
    global engine, async_engine, __async_session, __session

    engine = create_engine(
        (
            f"mysql+mysqldb://{settings.database.USERNAME}:{quote(settings.database.PASSWORD)}@"
            f"{settings.database.HOST}:{settings.database.PORT}/{settings.database.DATABASE}"
        ),
        pool_size=256,
        max_overflow=2048,
        pool_recycle=3600,
        echo=settings.DEBUG_ALCHEMY,
    )

    __session = sessionmaker(engine, autocommit=False)

    async_engine = create_async_engine(
        (
            f"mysql+asyncmy://{settings.database.USERNAME}:{quote(settings.database.PASSWORD)}@"
            f"{settings.database.HOST}:{settings.database.PORT}/{settings.database.DATABASE}"
        ),
        poolclass=AsyncAdaptedQueuePool,
        pool_size=10,
        max_overflow=2048,
        pool_recycle=3600,
        echo=settings.DEBUG_ALCHEMY,
    )

    __async_session = async_sessionmaker(
        async_engine, expire_on_commit=False, autoflush=False
    )


setup_db()


source_fk = Annotated[int, mapped_column(ForeignKey("source.id"))]

lock = asyncio.Lock()


def LocalSession() -> Session:
    global __session
    return __session()


def LocalAsyncSession() -> AsyncSession:
    global __async_session
    return __async_session()


class BaseModel(DeclarativeBase):
    pass


class Professor(BaseModel):
    __tablename__ = "professor"

    id: Mapped[big_intpk]
    nome: Mapped[str]
    email: Mapped[str]
    senha: Mapped[str]
    path_imagem: Mapped[str | None]
    cpf: Mapped[str] = mapped_column(VARCHAR(11))

    link_projetos: Mapped[list["ProjetoProfessor"]] = relationship(back_populates="professor")
    publicacoes: Mapped[list["Publicacao"]] = relationship(back_populates="professor")

    @staticmethod
    async def get_or_create(session: AsyncSession, nome: str, email: str, senha: str, cpf: str):
        just_created = False

        professor = await session.scalar(
            select(Professor).where(
                Professor.nome == nome,
                Professor.cpf == cpf,
            )
        )
        if not professor:
            professor = Professor(nome=nome, email=email, senha=senha, cpf=cpf)
            just_created = True
            session.add(professor)
            await session.commit()

        return professor, just_created


class Projeto(BaseModel):
    __tablename__ = "projeto"

    id: Mapped[big_intpk]
    titulo: Mapped[str]
    descricao: Mapped[text | None]
    path_imagem: Mapped[str]
    data_inicio: Mapped[timestamp]
    data_fim: Mapped[timestamp | None]
    status: Mapped[ProjetoStatusEnum] = mapped_column(default=ProjetoStatusEnum.ATIVO)
    publico: Mapped[str]
    curso_id: Mapped[int] = mapped_column(ForeignKey("curso.id"))

    link_professores: Mapped[list["ProjetoProfessor"]] = relationship(back_populates="projeto")
    publicacoes: Mapped[list["Publicacao"]] = relationship(back_populates="projeto")
    curso: Mapped["Curso"] = relationship(back_populates="projetos")

    @staticmethod
    async def get_or_create(session: AsyncSession, titulo: str, path_imagem: str, data_inicio: timestamp, status: ProjetoStatusEnum, publico: str, curso_id: int):
        just_created = False

        projeto = await session.scalar(
            select(Projeto).where(Projeto.titulo == titulo)
        )
        if not projeto:
            projeto = Projeto(
                titulo=titulo, path_imagem=path_imagem, data_inicio=data_inicio, status=status, publico=publico, curso_id=curso_id
            )
            just_created = True
            session.add(projeto)
            await session.commit()

        return projeto, just_created
    

class Curso(BaseModel):
    __tablename__ = "curso"

    id: Mapped[big_intpk]
    nome: Mapped[str]
    departamento_id: Mapped[int] = mapped_column(ForeignKey("departamento.id"))

    projetos: Mapped[list["Projeto"]] = relationship(back_populates="curso")
    departamento: Mapped["Departamento"] = relationship(back_populates="cursos")

    @staticmethod
    async def get_or_create(session: AsyncSession, nome: str, departamento_id: int):
        just_created = False

        curso = await session.scalar(
            select(Curso).where(Curso.nome == nome)
        )
        if not curso:
            curso = Curso(nome=nome, departamento_id=departamento_id)
            just_created = True
            session.add(curso)
            await session.commit()

        return curso, just_created
    

class Departamento(BaseModel):
    __tablename__ = "departamento"

    id: Mapped[big_intpk]
    nome: Mapped[str]
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"))

    cursos: Mapped[list["Curso"]] = relationship(back_populates="departamento")
    campus: Mapped["Campus"] = relationship(back_populates="departamentos")

    @staticmethod
    async def get_or_create(session: AsyncSession, nome: str, campus_id: int):
        just_created = False

        departamento = await session.scalar(
            select(Departamento).where(Departamento.nome == nome)
        )
        if not departamento:
            departamento = Departamento(nome=nome, campus_id=campus_id)
            just_created = True
            session.add(departamento)
            await session.commit()

        return departamento, just_created
    

class Campus(BaseModel):
    __tablename__ = "campus"

    id: Mapped[big_intpk]
    nome: Mapped[str]

    departamentos: Mapped[list["Departamento"]] = relationship(back_populates="campus")

    @staticmethod
    async def get_or_create(session: AsyncSession, nome: str):
        just_created = False

        campus = await session.scalar(
            select(Campus).where(Campus.nome == nome)
        )
        if not campus:
            campus = Campus(nome=nome)
            just_created = True
            session.add(campus)
            await session.commit()

        return campus, just_created
    

class Publicacao(BaseModel):
    __tablename__ = "publicacao"

    id: Mapped[big_intpk]
    titulo: Mapped[str]
    conteudo: Mapped[longtext]
    tipo: Mapped[PublicacaoTipoEnum]
    data_publicacao: Mapped[datetime_default_now]
    path_imagem: Mapped[str]
    professor_id: Mapped[int] = mapped_column(ForeignKey("professor.id"))
    projeto_id: Mapped[int] = mapped_column(ForeignKey("projeto.id"))

    professor: Mapped["Professor"] = relationship(back_populates="publicacoes")
    projeto: Mapped["Projeto"] = relationship(back_populates="publicacoes")

    @staticmethod
    async def get_or_create(session: AsyncSession, titulo: str, conteudo: str, tipo: PublicacaoTipoEnum, path_imagem: str, professor_id: int, projeto_id: int): 
        just_created = False

        publicacao = await session.scalar(
            select(Publicacao).where(Publicacao.titulo == titulo)
        )
        if not publicacao:
            publicacao = Publicacao(
                titulo=titulo, conteudo=conteudo, tipo=tipo, path_imagem=path_imagem, professor_id=professor_id, projeto_id=projeto_id
            )
            just_created = True
            session.add(publicacao)
            await session.commit()

        return publicacao, just_created
    

class Administrador(BaseModel):
    __tablename__ = "administrador"

    id: Mapped[big_intpk]
    nome: Mapped[str]
    email: Mapped[str]
    senha: Mapped[str]

    @staticmethod
    async def get_or_create(session: AsyncSession, nome: str, email: str, senha: str):
        just_created = False

        administrador = await session.scalar(
            select(Administrador).where(
                Administrador.nome == nome,
                Administrador.email == email,
            )
        )
        if not administrador:
            administrador = Administrador(nome=nome, email=email, senha=senha)
            just_created = True
            session.add(administrador)
            await session.commit()

        return administrador, just_created
    

class ProjetoProfessor(BaseModel):
    __tablename__ = "projeto_professor"
    __table_args__ = (UniqueConstraint("projeto_id", "professor_id"),)

    id: Mapped[big_intpk]
    projeto_id: Mapped[int] = mapped_column(ForeignKey("projeto.id"))
    professor_id: Mapped[int] = mapped_column(ForeignKey("professor.id"))

    projeto: Mapped["Projeto"] = relationship(back_populates="link_professores")
    professor: Mapped["Professor"] = relationship(back_populates="link_projetos")

    @staticmethod
    async def get_or_create(session: AsyncSession, projeto_id: str, professor_id: str):
        just_created = False

        projeto_professor = await session.scalar(
            select(ProjetoProfessor).where(
                ProjetoProfessor.projeto_id == projeto_id,
                ProjetoProfessor.professor_id == professor_id,
            )
        )
        if not projeto_professor:
            projeto_professor = ProjetoProfessor(projeto_id=projeto_id, professor_id=professor_id)
            just_created = True
            session.add(projeto_professor)
            await session.commit()

        return projeto_professor, just_created


async def create_all():
    async with async_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_all())
