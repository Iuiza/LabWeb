# app/main.py
from fastapi import FastAPI
from .routers import auth, admin, professores, projetos, postagens
# from .core.config import settings # Se você tiver um arquivo de configuração

app = FastAPI(
    title="Extensão UNEB em Foco API",
    description="API para gerenciar projetos de extensão, notícias e eventos da UNEB.", # <--- CORRIGIDO
    version="0.1.0"
)

# Incluir os routers
app.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
app.include_router(admin.router, prefix="/admin", tags=["Administração"])
app.include_router(professores.router, prefix="/professores", tags=["Professores"])
app.include_router(projetos.router, prefix="/projetos", tags=["Projetos"])
app.include_router(postagens.router, prefix="/postagens", tags=["Postagens (Notícias e Eventos)"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Bem-vindo à API Extensão UNEB em Foco!"}

# Configuração para servir arquivos estáticos e templates (se necessário)
# from fastapi.staticfiles import StaticFiles
# from pathlib import Path
# BASE_DIR = Path(__file__).resolve().parent
# app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")