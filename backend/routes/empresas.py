# routes/empresas.py — Nexus v1.0

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import Empresa, Usuario
from services.auth_service import hash_senha, decodificar_token, verificar_senha
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/empresas", tags=["empresas"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Schemas ───────────────────────────────────────────────────────────────────
class EmpresaCreate(BaseModel):
    razao_social:  str
    nome_fantasia: Optional[str] = None
    cnpj:          Optional[str] = None
    email:         str
    senha:         str
    telefone:      Optional[str] = None
    cep:           Optional[str] = None
    cidade:        Optional[str] = None
    endereco:      Optional[str] = None


class EmpresaUpdate(BaseModel):
    razao_social:  Optional[str] = None
    nome_fantasia: Optional[str] = None
    telefone:      Optional[str] = None
    cep:           Optional[str] = None
    cidade:        Optional[str] = None
    endereco:      Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_usuario_atual(token: str = Depends(oauth2)):
    payload = decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    return payload


def exigir_contador(usuario=Depends(get_usuario_atual)):
    if usuario["tipo"] != "contador":
        raise HTTPException(status_code=403, detail="Acesso restrito à contadora")
    return usuario


def _empresa_dict(e: Empresa) -> dict:
    return {
        "id":           e.id,
        "razao_social": e.razao_social,
        "nome_fantasia":e.nome_fantasia,
        "cnpj":         e.cnpj,
        "email":        e.email,
        "telefone":     e.telefone,
        "cep":          e.cep,
        "cidade":       e.cidade,
        "endereco":     e.endereco,
    }


# ── Rotas ─────────────────────────────────────────────────────────────────────
@router.get("/")
def listar_empresas(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_contador)
):
    """Lista todas as empresas ativas da contadora."""
    empresas = db.query(Empresa).filter(
        Empresa.contador_id == int(usuario["sub"]),
        Empresa.ativo == True
    ).all()
    return [_empresa_dict(e) for e in empresas]


@router.post("/")
def criar_empresa(
    dados: EmpresaCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_contador)
):
    """Cria uma nova empresa vinculada à contadora."""
    if db.query(Empresa).filter(Empresa.email == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    # Verifica CNPJ duplicado somente se foi informado
    if dados.cnpj:
        cnpj_limpo = dados.cnpj.replace(".", "").replace("/", "").replace("-", "")
        if db.query(Empresa).filter(Empresa.cnpj == dados.cnpj).first():
            raise HTTPException(status_code=400, detail="CNPJ já cadastrado")

    empresa = Empresa(
        razao_social  = dados.razao_social,
        nome_fantasia = dados.nome_fantasia,
        cnpj          = dados.cnpj,
        email         = dados.email,
        senha_hash    = hash_senha(dados.senha),
        telefone      = dados.telefone,
        cep           = dados.cep,
        cidade        = dados.cidade,
        endereco      = dados.endereco,
        contador_id   = int(usuario["sub"]),
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return {"id": empresa.id, "razao_social": empresa.razao_social}


@router.get("/{empresa_id}")
def get_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    """Retorna dados de uma empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if usuario["tipo"] == "cliente" and int(usuario["sub"]) != empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if usuario["tipo"] == "contador" and empresa.contador_id != int(usuario["sub"]):
        raise HTTPException(status_code=403, detail="Acesso negado")

    return _empresa_dict(empresa)


@router.patch("/{empresa_id}")
def atualizar_empresa(
    empresa_id: int,
    dados: EmpresaUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_contador)
):
    """Atualiza dados de uma empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if empresa.contador_id != int(usuario["sub"]):
        raise HTTPException(status_code=403, detail="Acesso negado")

    for campo, valor in dados.dict(exclude_none=True).items():
        setattr(empresa, campo, valor)

    db.commit()
    db.refresh(empresa)
    return {"ok": True, "empresa": _empresa_dict(empresa)}


@router.delete("/{empresa_id}")
def desativar_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_contador)
):
    """Desativa (soft delete) uma empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if empresa.contador_id != int(usuario["sub"]):
        raise HTTPException(status_code=403, detail="Acesso negado")

    empresa.ativo = False
    db.commit()
    return {"ok": True}
