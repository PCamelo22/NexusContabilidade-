# config.py — ElaConta v1.0

import os
from dotenv import load_dotenv

load_dotenv()

APP_NOME   = "ElaConta"
APP_VERSAO = "1.0"
APP_DESC   = "Contabilidade inteligente"

# ── Segurança ─────────────────────────────────────────────────────────────────
SECRET_KEY    = os.getenv("SECRET_KEY", "elaconta-secret-key-troque-em-producao")
ALGORITHM     = "HS256"
TOKEN_EXPIRY  = 60 * 24  # 24 horas em minutos

# ── Banco de dados ────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./elaconta.db")

# ── CORS ──────────────────────────────────────────────────────────────────────
_origens_raw   = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000")
ALLOWED_ORIGINS = [o.strip() for o in _origens_raw.split(",") if o.strip()]

# ── Upload ────────────────────────────────────────────────────────────────────
UPLOAD_DIR        = "uploads"
MAX_UPLOAD_MB     = 20
EXTENSOES_EXCEL   = [".xlsx", ".xls", ".csv"]
EXTENSOES_PDF     = [".pdf"]

# ── Thresholds de status (%) ──────────────────────────────────────────────────
STATUS_VERDE   = 100
STATUS_AMARELO = 40

# ── Cores ─────────────────────────────────────────────────────────────────────
CORES = {
    "purple":   "#6B21A8",
    "pink":     "#EC1E8C",
    "bg":       "#F5F3FF",
    "surface":  "#FFFFFF",
    "border":   "#EDE9FE",
    "texto":    "#1E1B4B",
    "muted":    "#6B7280",
    "verde":    "#10B981",
    "amarelo":  "#F59E0B",
    "vermelho": "#EF4444",
}

# ── Meses em português ────────────────────────────────────────────────────────
MESES = ["Jan","Fev","Mar","Abr","Mai","Jun",
         "Jul","Ago","Set","Out","Nov","Dez"]

# ── Categorias de lançamento ──────────────────────────────────────────────────
CATEGORIAS_RECEITA = [
    "Vendas",
    "Serviços",
    "Cartão de Crédito",
    "Cartão de Débito",
    "PIX Recebido",
    "Transferência Recebida",
    "Outras Receitas",
]

CATEGORIAS_DESPESA = [
    "Fornecedores",
    "Folha de Pagamento",
    "Aluguel",
    "Energia/Água/Internet",
    "Impostos",
    "Cartão Empresarial",
    "PIX Enviado",
    "Transferência Enviada",
    "Outras Despesas",
]