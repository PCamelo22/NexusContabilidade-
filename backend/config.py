# config.py — Nexus v1.0

import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

APP_NOME   = "Nexus Contabilidade"
APP_VERSAO = "1.0"
APP_DESC   = "Contabilidade inteligente"

# ── Modo de execução ──────────────────────────────────────────────────────────
# Render injeta a variável de ambiente RENDER=true automaticamente
IS_PRODUCTION = os.getenv("RENDER", "").lower() in ("true", "1", "yes")
IS_DEBUG = not IS_PRODUCTION

# ── Segurança ─────────────────────────────────────────────────────────────────
_DEFAULT_SECRET = "nexus-secret-key-troque-em-producao"
SECRET_KEY = os.getenv("SECRET_KEY", _DEFAULT_SECRET)

if SECRET_KEY == _DEFAULT_SECRET:
    if IS_PRODUCTION:
        # Em produção, impede a inicialização com chave fraca
        logger.critical(
            "🚨  SECRET_KEY padrão detectada em ambiente de produção (Render)! "
            "Defina a variável de ambiente SECRET_KEY com um valor seguro (≥32 caracteres) "
            "no painel do Render antes de iniciar."
        )
        sys.exit(1)
    else:
        logger.warning(
            "⚠️  SECRET_KEY padrão em uso — OK apenas em desenvolvimento local. "
            "Nunca use este valor em produção."
        )

ALGORITHM     = "HS256"
TOKEN_EXPIRY  = 60 * 24  # 24 horas em minutos

# ── Banco de dados ────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nexuscont.db")

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