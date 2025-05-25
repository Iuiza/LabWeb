import asyncio

from typing import Annotated, cast
from urllib.parse import quote
from sqlalchemy import (
    Engine,
    create_engine,
    ForeignKey,
    select
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
from enums.status import ProjetoStatusEnum, PublicacaoTipoEnum
from models.db_annotations import (
    varchar,
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
    nome: Mapped[varchar]
    email: Mapped[varchar]
    senha: Mapped[varchar]
    path_imagem: Mapped[varchar]
    cpf: Mapped[str] = mapped_column(VARCHAR(11))

    projetos: Mapped[list["Projeto"]] = relationship(back_populates="professores")
    publicacoes: Mapped[list["Publicacao"]] = relationship(back_populates="professor")

    @staticmethod
    async def get_or_create(session: AsyncSession, nome: str, email: str, senha: str, cpf: str, path_imagem: str):
        just_created = False

        professor = await session.scalar(
            select(Professor).where(
                Professor.nome == nome,
                Professor.cpf == cpf,
            )
        )
        if not professor:
            professor = Professor(nome=nome, email=email, senha=senha, path_imagem=path_imagem, cpf=cpf)
            just_created = True
            session.add(professor)
            await session.commit()

        return professor, just_created


class Projeto(BaseModel):
    __tablename__ = "projeto"

    id: Mapped[big_intpk]
    titulo: Mapped[varchar]
    descricao: Mapped[text | None]
    path_imagem: Mapped[varchar]
    data_inicio: Mapped[timestamp]
    data_fim: Mapped[timestamp | None]
    status: Mapped[ProjetoStatusEnum] = mapped_column(default=ProjetoStatusEnum.ATIVO)
    publico: Mapped[varchar]

    professores: Mapped[list["Professor"]] = relationship(back_populates="projetos")
    publicacoes: Mapped[list["Publicacao"]] = relationship(back_populates="projeto")
    curso: Mapped["Curso"] = relationship(back_populates="projetos")

    @staticmethod
    async def get_or_create(session: AsyncSession, titulo: str, path_imagem: str, data_inicio: timestamp, status: ProjetoStatusEnum, publico: str):
        just_created = False

        projeto = await session.scalar(
            select(Projeto).where(Projeto.titulo == titulo)
        )
        if not projeto:
            projeto = Projeto(
                titulo=titulo, path_imagem=path_imagem, data_inicio=data_inicio, status=status, publico=publico
            )
            just_created = True
            session.add(projeto)
            await session.commit()

        return projeto, just_created
    

class Curso(BaseModel):
    __tablename__ = "curso"

    id: Mapped[big_intpk]
    nome: Mapped[varchar]

    projetos: Mapped[list["Projeto"]] = relationship(back_populates="curso")
    departamento: Mapped["Departamento"] = relationship(back_populates="cursos")

    @staticmethod
    async def get_or_create(session: AsyncSession, nome: str):
        just_created = False

        curso = await session.scalar(
            select(Curso).where(Curso.nome == nome)
        )
        if not curso:
            curso = Curso(nome=nome)
            just_created = True
            session.add(curso)
            await session.commit()

        return curso, just_created
    

class Departamento(BaseModel):
    __tablename__ = "departamento"

    id: Mapped[big_intpk]
    nome: Mapped[varchar]

    cursos: Mapped[list["Curso"]] = relationship(back_populates="departamento")
    campus: Mapped["Campus"] = relationship(back_populates="departamentos")

    @staticmethod
    async def get_or_create(session: AsyncSession, nome: str):
        just_created = False

        departamento = await session.scalar(
            select(Departamento).where(Departamento.nome == nome)
        )
        if not departamento:
            departamento = Departamento(nome=nome)
            just_created = True
            session.add(departamento)
            await session.commit()

        return departamento, just_created
    

class Campus(BaseModel):
    __tablename__ = "campus"

    id: Mapped[big_intpk]
    nome: Mapped[varchar]

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
    titulo: Mapped[varchar]
    conteudo: Mapped[text | None]
    tipo: Mapped[PublicacaoTipoEnum]
    data_publicacao: Mapped[datetime_default_now]
    path_imagem: Mapped[timestamp]

    professor: Mapped["Professor"] = relationship(back_populates="publicacoes")
    projeto: Mapped["Projeto"] = relationship(back_populates="publicacoes")

    @staticmethod
    async def get_or_create(session: AsyncSession, titulo: str, conteudo: str, tipo: PublicacaoTipoEnum, path_imagem: str):
        just_created = False

        publicacao = await session.scalar(
            select(Publicacao).where(Publicacao.titulo == titulo)
        )
        if not publicacao:
            publicacao = Publicacao(
                titulo=titulo, conteudo=conteudo, tipo=tipo, path_imagem=path_imagem
            )
            just_created = True
            session.add(publicacao)
            await session.commit()

        return publicacao, just_created
    

class Administrador(BaseModel):
    __tablename__ = "administrador"

    id: Mapped[big_intpk]
    nome: Mapped[varchar]
    email: Mapped[varchar]
    senha: Mapped[varchar]

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


async def create_all():
    async with async_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_all())
