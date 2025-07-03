from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, admin, professores, projetos, postagens, campus, departamentos, cursos

app = FastAPI(
    title="Extensão UNEB em Foco API",
    description="API para gerenciar projetos de extensão, notícias e eventos da UNEB.",
    version="0.1.0"
)

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1:5500",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir os routers
app.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
app.include_router(admin.router, prefix="/admin", tags=["Administração"])
app.include_router(professores.router, prefix="/professores", tags=["Professores"])
app.include_router(projetos.router, prefix="/projetos", tags=["Projetos"])
app.include_router(postagens.router, prefix="/postagens", tags=["Postagens (Notícias e Eventos)"])
app.include_router(campus.router, prefix="/campus", tags=["Campus"])
app.include_router(departamentos.router, prefix="/departamentos", tags=["Departamentos"])
app.include_router(cursos.router, prefix="/cursos", tags=["Cursos"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Bem-vindo à API Extensão UNEB em Foco!"}
