# ─────────────────────────────────────────────────────────────────────────────
# main.py — ElaConta v1.0
# ─────────────────────────────────────────────────────────────────────────────

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from database import engine, SessionLocal, Base, migrar_colunas
from models import *
from services.auth_service import seed
from routes import auth, empresas, financeiro, uploads, cadastro
from config import APP_NOME, APP_VERSAO, ALLOWED_ORIGINS
from limiter import limiter

# ── Cria tabelas ──────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
migrar_colunas()   # adiciona colunas novas sem derrubar dados

# ── Seed inicial ──────────────────────────────────────────────────────────────
def init_db():
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()

init_db()

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=APP_NOME,
    version=APP_VERSAO,
    docs_url="/docs",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Headers de segurança HTTP ─────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]  = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["X-XSS-Protection"]        = "1; mode=block"
    response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
    return response

# ── Rotas API ─────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(empresas.router)
app.include_router(financeiro.router)
app.include_router(uploads.router)
app.include_router(cadastro.router)

# ── Arquivos estáticos (boletos, comprovantes) ────────────────────────────────
os.makedirs("uploads/boletos",      exist_ok=True)
os.makedirs("uploads/comprovantes", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ── Templates HTML ────────────────────────────────────────────────────────────
os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/cadastro", response_class=HTMLResponse)
def cadastro_page(request: Request):
    return templates.TemplateResponse("cadastro.html", {"request": request})

@app.get("/conhecer", response_class=HTMLResponse)
def conhecer_page(request: Request):
    return templates.TemplateResponse("conhecer.html", {"request": request})

@app.get("/cliente", response_class=HTMLResponse)
def cliente_page(request: Request):
    return templates.TemplateResponse("cliente.html", {"request": request})

@app.get("/contador", response_class=HTMLResponse)
def contador_page(request: Request):
    return templates.TemplateResponse("contador.html", {"request": request})

@app.get("/recuperar-senha", response_class=HTMLResponse)
def recuperar_senha_page(request: Request):
    return templates.TemplateResponse("recuperar-senha.html", {"request": request})

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NOME, "versao": APP_VERSAO}
