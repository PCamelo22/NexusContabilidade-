# routes/cadastro.py — ElaConta v1.0

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from database import get_db
from models import Usuario, TipoUsuario
from services.auth_service import hash_senha
from services.email_service import gerar_codigo, enviar_codigo, enviar_solicitacao
from limiter import limiter

router = APIRouter(prefix="/cadastro", tags=["cadastro"])

# Armazenamento temporário de códigos { email: { codigo, expira, dados } }
_codigos: dict = {}


# ── Schemas ───────────────────────────────────────────────────────────────────
class SolicitarCadastro(BaseModel):
    nome:  str
    email: str
    senha: str


class ConfirmarCadastro(BaseModel):
    email:  str
    codigo: str


class Solicitacao(BaseModel):
    nome:        str
    cnpj:        Optional[str] = None
    email:       str
    telefone:    str
    segmento:    str
    porte:       str
    faturamento: str
    mensagem:    Optional[str] = None
    honorario:   Optional[str] = None


# ── Rotas ─────────────────────────────────────────────────────────────────────
@router.post("/solicitar")
@limiter.limit("5/minute")
def solicitar_cadastro(request: Request, dados: SolicitarCadastro, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    codigo = gerar_codigo()
    _codigos[dados.email] = {
        "codigo": codigo,
        "expira": datetime.utcnow() + timedelta(minutes=10),
        "dados":  dados.dict(),
    }

    ok = enviar_codigo(dados.email, codigo, dados.nome)
    if not ok:
        # E-mail não configurado ou falhou — retorna o código no response para testes
        import os
        if not os.getenv("EMAIL_REMETENTE") or not os.getenv("EMAIL_SENHA"):
            return {
                "ok": True,
                "mensagem": f"E-mail não configurado. Use o código abaixo para confirmar.",
                "codigo_debug": codigo   # visível apenas quando email não está configurado
            }
        raise HTTPException(status_code=500, detail="Erro ao enviar e-mail. Verifique as configurações.")

    return {"ok": True, "mensagem": f"Código enviado para {dados.email}"}


@router.post("/confirmar")
def confirmar_cadastro(body: ConfirmarCadastro, db: Session = Depends(get_db)):
    entrada = _codigos.get(body.email)

    if not entrada:
        raise HTTPException(status_code=400, detail="Nenhuma solicitação encontrada para este e-mail.")

    if datetime.utcnow() > entrada["expira"]:
        del _codigos[body.email]
        raise HTTPException(status_code=400, detail="Código expirado. Solicite um novo.")

    if entrada["codigo"] != body.codigo:
        raise HTTPException(status_code=400, detail="Código incorreto.")

    dados = entrada["dados"]
    usuario = Usuario(
        nome       = dados["nome"],
        email      = dados["email"],
        senha_hash = hash_senha(dados["senha"]),
        tipo       = TipoUsuario.contador,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    del _codigos[body.email]

    return {"ok": True, "mensagem": "Cadastro realizado com sucesso!"}


@router.get("/status-email")
def status_email():
    """Verifica se as credenciais de e-mail estão configuradas (sem expor senha)."""
    import os
    remetente = os.getenv("EMAIL_REMETENTE")
    senha     = os.getenv("EMAIL_SENHA")
    if not remetente or not senha:
        return {
            "configurado": False,
            "mensagem": "EMAIL_REMETENTE ou EMAIL_SENHA não definidos nas variáveis de ambiente.",
            "dica": "Configure no Render > Environment > Add Environment Variable"
        }
    return {
        "configurado": True,
        "remetente": remetente,
        "mensagem": "Credenciais configuradas. Use /cadastro/testar-email para enviar um e-mail de teste."
    }


@router.post("/testar-email")
def testar_email(email_destino: str):
    """Envia e-mail de teste para verificar se o SMTP está funcionando."""
    from services.email_service import enviar_codigo
    import os
    if not os.getenv("EMAIL_REMETENTE"):
        raise HTTPException(status_code=400, detail="E-mail não configurado nas variáveis de ambiente.")
    ok = enviar_codigo(email_destino, "123456", "Teste")
    if ok:
        return {"ok": True, "mensagem": f"E-mail de teste enviado para {email_destino}"}
    raise HTTPException(status_code=500, detail="Falha ao enviar. Verifique EMAIL_REMETENTE, EMAIL_SENHA e se a Senha de App do Gmail está correta.")


@router.post("/reenviar")
def reenviar_codigo(email: str, db: Session = Depends(get_db)):
    entrada = _codigos.get(email)
    if not entrada:
        raise HTTPException(status_code=400, detail="Nenhuma solicitação pendente para este e-mail.")

    codigo = gerar_codigo()
    entrada["codigo"] = codigo
    entrada["expira"] = datetime.utcnow() + timedelta(minutes=10)

    ok = enviar_codigo(email, codigo, entrada["dados"]["nome"])
    if not ok:
        raise HTTPException(status_code=500, detail="Erro ao reenviar e-mail.")

    return {"ok": True, "mensagem": "Código reenviado!"}


@router.post("/solicitacao")
def receber_solicitacao(dados: Solicitacao):
    ok = enviar_solicitacao(dados)
    if not ok:
        raise HTTPException(status_code=500, detail="Erro ao enviar solicitação.")
    return {"ok": True}
