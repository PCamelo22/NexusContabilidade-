# routes/auth.py — ElaConta v1.0

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from database import get_db
from models import Usuario, Empresa
from services.auth_service import autenticar_usuario, criar_token, hash_senha
from services.email_service import gerar_codigo, enviar_recuperacao
from limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

_codigos_recuperacao: dict = {}

# ── Bloqueio temporário por tentativas falhas ─────────────────────────────────
# { "email": {"tentativas": int, "bloqueado_ate": datetime | None} }
_tentativas_login: dict = {}
_MAX_TENTATIVAS  = 5
_BLOQUEIO_MINUTOS = 15


def _verificar_bloqueio(email: str):
    """Lança 429 se o e-mail estiver temporariamente bloqueado."""
    estado = _tentativas_login.get(email)
    if not estado:
        return
    if estado.get("bloqueado_ate") and datetime.utcnow() < estado["bloqueado_ate"]:
        restante = int((estado["bloqueado_ate"] - datetime.utcnow()).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Conta temporariamente bloqueada por {_BLOQUEIO_MINUTOS} min "
                f"após {_MAX_TENTATIVAS} tentativas incorretas. "
                f"Tente novamente em {restante} min."
            ),
        )
    # Bloqueio expirado — limpa o registro
    if estado.get("bloqueado_ate") and datetime.utcnow() >= estado["bloqueado_ate"]:
        del _tentativas_login[email]


def _registrar_falha(email: str):
    """Incrementa contador; bloqueia se atingir o limite."""
    estado = _tentativas_login.setdefault(email, {"tentativas": 0, "bloqueado_ate": None})
    estado["tentativas"] += 1
    if estado["tentativas"] >= _MAX_TENTATIVAS:
        estado["bloqueado_ate"] = datetime.utcnow() + timedelta(minutes=_BLOQUEIO_MINUTOS)


def _registrar_sucesso(email: str):
    """Zera o contador em caso de login bem-sucedido."""
    _tentativas_login.pop(email, None)


# ── Schemas ───────────────────────────────────────────────────────────────────
class LoginInput(BaseModel):
    email: str
    senha: str


class RecuperarSenha(BaseModel):
    email: str


class RedefinirSenha(BaseModel):
    email:      str
    codigo:     str
    nova_senha: str


# ── Rotas ─────────────────────────────────────────────────────────────────────
@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, dados: LoginInput, db: Session = Depends(get_db)):
    email_norm = dados.email.strip().lower()

    # Verificar se a conta está temporariamente bloqueada
    _verificar_bloqueio(email_norm)

    usuario = autenticar_usuario(db, dados.email, dados.senha)

    if not usuario:
        _registrar_falha(email_norm)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos"
        )

    # Contadoras precisam de aprovação para acessar o sistema
    if usuario["tipo"] == "contador" and not usuario.get("aprovado", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadastro aguardando aprovação da contadora responsável. Você receberá um e-mail quando for aprovado."
        )

    _registrar_sucesso(email_norm)

    token = criar_token({
        "sub":  str(usuario["id"]),
        "tipo": usuario["tipo"],
        "nome": usuario["nome"],
    })

    return {
        "access_token": token,
        "token_type":   "bearer",
        "usuario":      usuario,
    }


@router.post("/recuperar")
@limiter.limit("5/minute")
def recuperar_senha(request: Request, dados: RecuperarSenha, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == dados.email, Usuario.ativo == True).first()
    empresa = db.query(Empresa).filter(Empresa.email == dados.email, Empresa.ativo == True).first()

    if usuario or empresa:
        nome   = usuario.nome if usuario else empresa.razao_social
        codigo = gerar_codigo()
        _codigos_recuperacao[dados.email] = {
            "codigo": codigo,
            "expira": datetime.utcnow() + timedelta(minutes=10),
            "tipo":   "usuario" if usuario else "empresa",
        }
        enviar_recuperacao(dados.email, codigo, nome)

    # Resposta genérica para não revelar se o e-mail existe
    return {"ok": True, "mensagem": "Se o e-mail existir, enviaremos as instruções."}


@router.post("/redefinir")
def redefinir_senha(dados: RedefinirSenha, db: Session = Depends(get_db)):
    entrada = _codigos_recuperacao.get(dados.email)

    if not entrada:
        raise HTTPException(status_code=400, detail="Nenhuma solicitação encontrada.")

    if datetime.utcnow() > entrada["expira"]:
        del _codigos_recuperacao[dados.email]
        raise HTTPException(status_code=400, detail="Código expirado. Solicite um novo.")

    if entrada["codigo"] != dados.codigo:
        raise HTTPException(status_code=400, detail="Código incorreto.")

    if len(dados.nova_senha) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres.")

    nova_hash = hash_senha(dados.nova_senha)

    if entrada["tipo"] == "usuario":
        u = db.query(Usuario).filter(Usuario.email == dados.email).first()
        if u:
            u.senha_hash = nova_hash
    else:
        e = db.query(Empresa).filter(Empresa.email == dados.email).first()
        if e:
            e.senha_hash = nova_hash

    db.commit()
    del _codigos_recuperacao[dados.email]
    return {"ok": True, "mensagem": "Senha redefinida com sucesso!"}
