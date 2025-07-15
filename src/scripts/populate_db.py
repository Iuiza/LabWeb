import asyncio
import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.future import select

# Importe seus modelos e a sessão do banco de dados
# Certifique-se de que os caminhos de importação estão corretos
from models.db import (
    LocalAsyncSession,
    Campus,
    Departamento,
    Curso,
    Professor,
    Projeto,
    Publicacao,
    Administrador,
    ProjetoProfessor,
    create_all,
)
from enums.status import ProjetoStatusEnum
from enums.tipo import PublicacaoTipoEnum

# Inicializa o Faker para gerar dados fictícios
fake = Faker('pt_BR')

async def populate_data():
    """
    Popula todas as tabelas do banco de dados com dados fictícios,
    respeitando as dependências entre elas.
    """
    # Garante que todas as tabelas foram criadas antes de popular
    await create_all()

    async with LocalAsyncSession() as session:
        print("Iniciando o povoamento do banco de dados...")

        # --- 1. Criar Administradores ---
        print("Criando administradores...")
        for _ in range(3):
            await Administrador.get_or_create(
                session=session,
                nome=fake.name(),
                email=fake.unique.email(),
                senha=fake.password() # Em um app real, use hash!
            )

        # --- 2. Criar Campus ---
        print("Criando campus...")
        campi = []
        for nome_campus in ["Campus Principal", "Campus SECENE", "Campus Avançado"]:
            campus, _ = await Campus.get_or_create(session=session, nome=nome_campus)
            campi.append(campus)

        # --- 3. Criar Departamentos ---
        print("Criando departamentos...")
        departamentos = []
        for campus in campi:
            for _ in range(2):
                depto, _ = await Departamento.get_or_create(
                    session=session,
                    nome=f"Departamento de {fake.job().split(' ')[-1]}",
                    campus_id=campus.id
                )
                departamentos.append(depto)

        # --- 4. Criar Cursos ---
        print("Criando cursos...")
        cursos = []
        for depto in departamentos:
            for _ in range(3):
                curso, _ = await Curso.get_or_create(
                    session=session,
                    nome=f"Curso de {fake.bs()}",
                    departamento_id=depto.id
                )
                cursos.append(curso)

        # --- 5. Criar Professores ---
        print("Criando professores...")
        professores = []
        for _ in range(15):
            professor, _ = await Professor.get_or_create(
                session=session,
                nome=fake.name(),
                email=fake.unique.email(),
                senha=fake.password(), # Lembre-se de usar hash em produção
                cpf=fake.unique.cpf().replace('.', '').replace('-', '')
            )
            professores.append(professor)

        # --- 6. Criar Projetos ---
        print("Criando projetos...")
        projetos = []
        for _ in range(20):
            data_inicio = fake.date_time_this_decade()
            projeto, _ = await Projeto.get_or_create(
                session=session,
                titulo=f"Projeto {fake.catch_phrase()}",
                path_imagem=fake.image_url(),
                data_inicio=data_inicio,
                status=random.choice(list(ProjetoStatusEnum)),
                publico=random.choice(["Alunos de Graduação", "Comunidade Externa", "Pesquisadores"]),
                curso_id=random.choice(cursos).id
            )
            projetos.append(projeto)

        # --- 7. Vincular Professores a Projetos (Muitos-para-Muitos) ---
        print("Vinculando professores a projetos...")
        for projeto in projetos:
            # Vincula de 1 a 3 professores por projeto
            professores_do_projeto = random.sample(professores, k=random.randint(1, 3))
            for professor in professores_do_projeto:
                await ProjetoProfessor.get_or_create(
                    session=session,
                    projeto_id=projeto.id,
                    professor_id=professor.id
                )

        # --- 8. Criar Publicações ---
        print("Criando publicações...")
        for projeto in projetos:
            # Busca os professores vinculados a este projeto
            stmt = select(ProjetoProfessor).where(ProjetoProfessor.projeto_id == projeto.id)
            links = (await session.execute(stmt)).scalars().all()
            if not links:
                continue
            
            # Cria de 1 a 4 publicações por projeto
            for _ in range(random.randint(1, 4)):
                professor_id_aleatorio = random.choice(links).professor_id
                await Publicacao.get_or_create(
                    session=session,
                    titulo=f"Artigo sobre {projeto.titulo}: {fake.sentence(nb_words=4)}",
                    conteudo=fake.text(max_nb_chars=1000),
                    tipo=random.choice(list(PublicacaoTipoEnum)),
                    path_imagem=fake.image_url(),
                    professor_id=professor_id_aleatorio,
                    projeto_id=projeto.id
                )

        await session.commit()
        print("\n✅ Povoamento do banco de dados concluído com sucesso!")

def main():
    """Função de entrada para o script."""
    print("Iniciando o povoamento do banco de dados via Poetry script...")
    asyncio.run(populate_data())

if __name__ == "__main__":
    main()
