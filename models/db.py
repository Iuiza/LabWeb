import asyncio

from datetime import datetime, date, timedelta
from typing import Annotated, Any, Self, ClassVar, cast
from urllib.parse import quote
from sqlalchemy import (
    Engine,
    Index,
    create_engine,
    ForeignKey,
    select,
    DATE,
    UniqueConstraint,
    DATETIME,
    and_,
    or_,
    JSON,
    func,
    Float,
    event,
    update,
)
from sqlalchemy.dialects.mysql import TEXT, VARCHAR
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
    selectinload,
    Session,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from config import settings
from models.db_annotations import (
    intpk,
    varchar,
    text,
    timestamp,
    datetime_default_now,
    big_int,
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
    cpf: Mapped[str] = mapped_column(VARCHAR(11))

    projetos: Mapped[list["Projeto"]] = relationship(back_populates="professores")

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
    titulo: Mapped[varchar]
    descricao: Mapped[text | None]
    path_imagem: Mapped[varchar | None]
    data_inicio: Mapped[timestamp]
    data_fim: Mapped[timestamp | None]
    status: Mapped[ProjetoStatusEnum] = mapped_column(default=ProjetoStatusEnum.ATIVO)
    publico: Mapped[varchar]

    professores: Mapped[list["Professor"]] = relationship(back_populates="projetos")
    curso: Mapped["Curso"] = relationship(back_populates="projetos")

    @staticmethod
    async def get_or_create(session: AsyncSession, titulo: str, data_inicio: timestamp, status: ProjetoStatusEnum, publico: str):
        just_created = False

        projeto = await session.scalar(
            select(Projeto).where(Projeto.titulo == titulo)
        )
        if not projeto:
            projeto = Projeto(
                titulo=titulo, data_inicio=data_inicio, status=status, publico=publico
            )
            just_created = True
            session.add(projeto)
            await session.commit()

        return projeto, just_created


async def create_all():
    async with async_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_all())
