# routes/aprovacoes.py — ElaConta v1.0

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario, TipoUsuario
from services.auth_service import decodificar_token
from services.email_service import enviar_aprovacao
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/aprovacoes", tags=["aprovacoes"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def exigir_contador(token: str = Depends(oauth2)):
    payload = decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    if payload.get("tipo") != "contador":
        raise HTTPException(status_code=403, detail="Acesso restrito à contadora")
    return payload


@router.get("/pendentes")
def listar_pendentes(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_contador)
):
    """Lista contadoras cadastradas que ainda não foram aprovadas."""
    pendentes = db.query(Usuario).filter(
        Usuario.tipo     == TipoUsuario.contador,
        Usuario.aprovado == False,
        Usuario.ativo    == True,
    ).all()
    return [
        {
            "id":        u.id,
            "nome":      u.nome,
            "email":     u.email,
            "criado_em": u.criado_em.strftime("%d/%m/%Y %H:%M") if u.criado_em else "—",
        }
        for u in pendentes
    ]


@router.patch("/{usuario_id}/aprovar")
def aprovar(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_contador)
):
    """Aprova o acesso de uma contadora cadastrada."""
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if u.tipo != TipoUsuario.contador:
        raise HTTPException(status_code=400, detail="Apenas contadoras podem ser aprovadas")

    u.aprovado = True
    db.commit()
    enviar_aprovacao(u.email, u.nome, aprovado=True)
    return {"ok": True, "mensagem": f"{u.nome} aprovada com sucesso!"}


@router.patch("/{usuario_id}/rejeitar")
def rejeitar(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_contador)
):
    """Rejeita e desativa uma contadora cadastrada."""
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    u.aprovado = False
    u.ativo    = False   # desativa a conta
    db.commit()
    enviar_aprovacao(u.email, u.nome, aprovado=False)
    return {"ok": True, "mensagem": f"Cadastro de {u.nome} rejeitado."}
