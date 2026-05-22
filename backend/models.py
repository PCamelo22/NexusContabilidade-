# ─────────────────────────────────────────────────────────────────────────────
# models.py — ElaConta v1.0
# ─────────────────────────────────────────────────────────────────────────────

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class TipoUsuario(str, enum.Enum):
    contador = "contador"
    cliente  = "cliente"


class TipoLancamento(str, enum.Enum):
    receita = "receita"
    despesa = "despesa"


class StatusLancamento(str, enum.Enum):
    pendente   = "pendente"
    confirmado = "confirmado"
    cancelado  = "cancelado"


# ── Usuário ───────────────────────────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id         = Column(Integer, primary_key=True, index=True)
    nome       = Column(String(255), nullable=False)
    email      = Column(String(255), unique=True, index=True, nullable=False)
    senha_hash = Column(String(512), nullable=False)
    tipo       = Column(Enum(TipoUsuario), nullable=False)
    ativo      = Column(Boolean, default=True)
    aprovado   = Column(Boolean, default=False)   # True = contadora aprovou o acesso
    criado_em  = Column(DateTime, server_default=func.now())

    empresas   = relationship("Empresa", back_populates="contador", foreign_keys="Empresa.contador_id")


# ── Empresa ───────────────────────────────────────────────────────────────────
class Empresa(Base):
    __tablename__ = "empresas"

    id            = Column(Integer, primary_key=True, index=True)
    razao_social  = Column(String(255), nullable=False)
    nome_fantasia = Column(String(255))
    cnpj          = Column(String(20),  unique=True, index=True)
    email         = Column(String(255), unique=True, index=True)
    senha_hash    = Column(String(512), nullable=False)
    telefone      = Column(String(30))
    cep           = Column(String(10))
    cidade        = Column(String(100))
    endereco      = Column(String(500))
    ativo         = Column(Boolean, default=True)
    criado_em     = Column(DateTime, server_default=func.now())

    contador_id   = Column(Integer, ForeignKey("usuarios.id"))
    contador      = relationship("Usuario", back_populates="empresas", foreign_keys=[contador_id])
    lancamentos   = relationship("Lancamento", back_populates="empresa")
    contas_pagar  = relationship("ContaPagar",  back_populates="empresa")


# ── Lançamento ────────────────────────────────────────────────────────────────
class Lancamento(Base):
    __tablename__ = "lancamentos"

    id          = Column(Integer, primary_key=True, index=True)
    empresa_id  = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    data        = Column(String(10),  nullable=False)   # YYYY-MM-DD
    descricao   = Column(String(500), nullable=False)
    categoria   = Column(String(100), nullable=False)
    tipo        = Column(Enum(TipoLancamento), nullable=False)
    valor       = Column(Float, nullable=False)
    status      = Column(Enum(StatusLancamento), default=StatusLancamento.confirmado)
    origem      = Column(String(20), default="manual")  # manual | excel | pdf
    observacao  = Column(Text)
    criado_em   = Column(DateTime, server_default=func.now())
    criado_por  = Column(Integer, ForeignKey("usuarios.id"))

    empresa     = relationship("Empresa", back_populates="lancamentos")


# ── Conta a Pagar ─────────────────────────────────────────────────────────────
class ContaPagar(Base):
    __tablename__ = "contas_pagar"

    id              = Column(Integer, primary_key=True, index=True)
    empresa_id      = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    descricao       = Column(String(500), nullable=False)
    valor           = Column(Float, nullable=False)
    vencimento      = Column(String(10), nullable=False)   # YYYY-MM-DD
    categoria       = Column(String(100))
    codigo_barras   = Column(String(200))   # linha digitável do boleto
    arquivo_url     = Column(String(500))   # caminho do PDF do boleto
    comprovante_url = Column(String(500))   # comprovante de pagamento enviado pelo cliente
    pago            = Column(Boolean, default=False)
    recorrente      = Column(Boolean, default=False)   # gera parcelas automáticas
    frequencia      = Column(String(20))               # mensal | trimestral | semestral | anual
    recorrencia_id  = Column(Integer)                  # agrupa parcelas da mesma recorrência
    criado_em       = Column(DateTime, server_default=func.now())
    criado_por      = Column(Integer, ForeignKey("usuarios.id"))

    empresa         = relationship("Empresa", back_populates="contas_pagar")
