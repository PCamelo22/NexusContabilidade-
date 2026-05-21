# routes/financeiro.py — ElaConta v1.0

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Optional, Literal
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from database import get_db
from models import Lancamento, ContaPagar, Empresa, TipoLancamento, StatusLancamento
from services.auth_service import decodificar_token
from services.email_service import enviar_nova_conta
from fastapi.security import OAuth2PasswordBearer
import threading

router = APIRouter(prefix="/financeiro", tags=["financeiro"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_usuario_atual(token: str = Depends(oauth2)):
    payload = decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    return payload


def verificar_acesso_empresa(usuario: dict, empresa_id: int, db: Session):
    """
    Cliente → acessa somente a própria empresa (sub == empresa_id).
    Contador → acessa somente empresas que gerencia.
    """
    if usuario["tipo"] == "cliente":
        if int(usuario["sub"]) != empresa_id:
            raise HTTPException(status_code=403, detail="Acesso negado")
    else:
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa or empresa.contador_id != int(usuario["sub"]):
            raise HTTPException(status_code=403, detail="Acesso negado")


def filtro_mes_ano(query, modelo, mes: int, ano: int):
    """Filtra por mês/ano via LIKE — compatível com SQLite e MySQL/PostgreSQL."""
    prefixo = f"{ano}-{mes:02d}-%"
    return query.filter(modelo.data.like(prefixo))


# ── Schemas ───────────────────────────────────────────────────────────────────
class LancamentoCreate(BaseModel):
    data:       str
    descricao:  str
    categoria:  str
    tipo:       Literal["receita", "despesa"]   # ← validação estrita
    valor:      float
    observacao: Optional[str] = None

    @validator("data")
    def validar_data(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Data deve estar no formato YYYY-MM-DD")
        return v

    @validator("valor")
    def validar_valor(cls, v):
        if v <= 0:
            raise ValueError("Valor deve ser positivo")
        return v


class ContaPagarCreate(BaseModel):
    descricao:     str
    valor:         float
    vencimento:    str
    categoria:     Optional[str] = None
    codigo_barras: Optional[str] = None
    recorrente:    bool = False
    frequencia:    Optional[Literal["mensal","trimestral","semestral","anual"]] = None

    @validator("vencimento")
    def validar_vencimento(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Vencimento deve estar no formato YYYY-MM-DD")
        return v

    @validator("valor")
    def validar_valor(cls, v):
        if v <= 0:
            raise ValueError("Valor deve ser positivo")
        return v


# ── Dashboard ─────────────────────────────────────────────────────────────────
@router.get("/dashboard/{empresa_id}")
def dashboard(
    empresa_id: int,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)

    hoje = datetime.today()
    mes  = mes or hoje.month
    ano  = ano or hoje.year

    q = db.query(Lancamento).filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.status     == StatusLancamento.confirmado,
    )
    lancamentos = filtro_mes_ano(q, Lancamento, mes, ano).all()

    receitas    = sum(l.valor for l in lancamentos if l.tipo == TipoLancamento.receita)
    despesas    = sum(l.valor for l in lancamentos if l.tipo == TipoLancamento.despesa)
    saldo       = receitas - despesas

    contas      = db.query(ContaPagar).filter(
        ContaPagar.empresa_id == empresa_id,
        ContaPagar.pago       == False,
    ).all()
    total_pagar = sum(c.valor for c in contas)

    evolucao = []
    for m in range(5, -1, -1):
        ref = date.today().replace(day=1) - relativedelta(months=m)
        q_ref = db.query(Lancamento).filter(
            Lancamento.empresa_id == empresa_id,
            Lancamento.status     == StatusLancamento.confirmado,
        )
        lm = filtro_mes_ano(q_ref, Lancamento, ref.month, ref.year).all()
        evolucao.append({
            "mes":      f"{ref.month:02d}/{ref.year}",
            "receitas": sum(l.valor for l in lm if l.tipo == TipoLancamento.receita),
            "despesas": sum(l.valor for l in lm if l.tipo == TipoLancamento.despesa),
        })

    return {
        "mes":         mes,
        "ano":         ano,
        "receitas":    receitas,
        "despesas":    despesas,
        "saldo":       saldo,
        "total_pagar": total_pagar,
        "evolucao":    evolucao,
    }


# ── Lançamentos ───────────────────────────────────────────────────────────────
@router.get("/lancamentos/{empresa_id}")
def listar_lancamentos(
    empresa_id: int,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)

    query = db.query(Lancamento).filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.status     != StatusLancamento.cancelado,
    )

    if mes and ano:
        query = filtro_mes_ano(query, Lancamento, mes, ano)
    elif ano:
        query = query.filter(Lancamento.data.like(f"{ano}-%"))
    elif mes:
        query = query.filter(Lancamento.data.like(f"%-{mes:02d}-%"))

    if tipo:
        query = query.filter(Lancamento.tipo == tipo)

    lancamentos = query.order_by(Lancamento.data.desc()).all()

    return [
        {
            "id":         l.id,
            "data":       l.data,
            "descricao":  l.descricao,
            "categoria":  l.categoria,
            "tipo":       l.tipo.value,
            "valor":      l.valor,
            "status":     l.status.value,
            "origem":     l.origem,
            "observacao": l.observacao,   # ← incluído na resposta
        }
        for l in lancamentos
    ]


@router.post("/lancamentos/{empresa_id}")
def criar_lancamento(
    empresa_id: int,
    dados: LancamentoCreate,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)

    lancamento = Lancamento(
        empresa_id = empresa_id,
        data       = dados.data,
        descricao  = dados.descricao,
        categoria  = dados.categoria,
        tipo       = dados.tipo,
        valor      = dados.valor,
        observacao = dados.observacao,
        origem     = "manual",
        status     = StatusLancamento.confirmado,
        criado_por = int(usuario["sub"]),
    )
    db.add(lancamento)
    db.commit()
    db.refresh(lancamento)
    return {"id": lancamento.id, "ok": True}


@router.delete("/lancamentos/{lancamento_id}")
def deletar_lancamento(
    lancamento_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    l = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    verificar_acesso_empresa(usuario, l.empresa_id, db)

    l.status = StatusLancamento.cancelado
    db.commit()
    return {"ok": True}


# ── Helper ───────────────────────────────────────────────────────────────────
def _conta_dict(c) -> dict:
    return {
        "id":              c.id,
        "empresa_id":      c.empresa_id,
        "descricao":       c.descricao,
        "valor":           c.valor,
        "vencimento":      c.vencimento,
        "categoria":       c.categoria,
        "codigo_barras":   c.codigo_barras,
        "arquivo_url":     c.arquivo_url,
        "comprovante_url": c.comprovante_url,
        "pago":            c.pago,
        "recorrente":      bool(c.recorrente),
        "frequencia":      c.frequencia,
        "recorrencia_id":  c.recorrencia_id,
        "criado_em":       c.criado_em.isoformat() if c.criado_em else None,
    }


# ── Contas a pagar ────────────────────────────────────────────────────────────
@router.get("/contas-pagar/{empresa_id}")
def listar_contas(
    empresa_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)
    contas = db.query(ContaPagar).filter(
        ContaPagar.empresa_id == empresa_id
    ).order_by(ContaPagar.vencimento).all()

    return [_conta_dict(c) for c in contas]


@router.get("/contas-pagar-todas")
def listar_todas_contas(
    pago: Optional[bool] = None,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    """Contadora: lista contas de TODAS as suas empresas."""
    if usuario["tipo"] != "contador":
        raise HTTPException(status_code=403, detail="Acesso restrito à contadora")

    from models import Empresa
    ids_empresas = [
        e.id for e in db.query(Empresa).filter(
            Empresa.contador_id == int(usuario["sub"]),
            Empresa.ativo == True
        ).all()
    ]

    query = db.query(ContaPagar).filter(ContaPagar.empresa_id.in_(ids_empresas))
    if pago is not None:
        query = query.filter(ContaPagar.pago == pago)

    contas = query.order_by(ContaPagar.vencimento).all()

    # inclui nome da empresa em cada item
    empresas_map = {
        e.id: e.razao_social
        for e in db.query(Empresa).filter(Empresa.id.in_(ids_empresas)).all()
    }
    result = []
    for c in contas:
        d = _conta_dict(c)
        d["empresa_nome"] = empresas_map.get(c.empresa_id, "—")
        result.append(d)
    return result


@router.post("/contas-pagar/{empresa_id}")
def criar_conta(
    request: Request,
    empresa_id: int,
    dados: ContaPagarCreate,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()

    # ── calcula intervalos para recorrência ───────────────────────────────────
    _delta = {
        "mensal":      relativedelta(months=1),
        "trimestral":  relativedelta(months=3),
        "semestral":   relativedelta(months=6),
        "anual":       relativedelta(years=1),
    }
    parcelas = 1
    if dados.recorrente and dados.frequencia:
        parcelas = {"mensal": 12, "trimestral": 4, "semestral": 2, "anual": 2}[dados.frequencia]

    ids_criados = []
    data_base   = datetime.strptime(dados.vencimento, "%Y-%m-%d").date()
    rec_id      = None   # será preenchido após 1ª parcela para agrupamento

    for i in range(parcelas):
        venc = data_base + (_delta[dados.frequencia] * i if dados.frequencia else relativedelta())
        desc = dados.descricao
        if parcelas > 1:
            desc = f"{dados.descricao} ({i+1}/{parcelas})"

        conta = ContaPagar(
            empresa_id    = empresa_id,
            descricao     = desc,
            valor         = dados.valor,
            vencimento    = venc.strftime("%Y-%m-%d"),
            categoria     = dados.categoria,
            codigo_barras = dados.codigo_barras,
            recorrente    = dados.recorrente,
            frequencia    = dados.frequencia,
            criado_por    = int(usuario["sub"]),
        )
        db.add(conta)
        db.flush()

        if i == 0:
            rec_id = conta.id     # usa o ID da 1ª parcela como chave de grupo
        if dados.recorrente:
            conta.recorrencia_id = rec_id

    db.commit()

    # ── envia e-mail em background (não bloqueia a resposta) ─────────────────
    if empresa and empresa.email:
        base = str(request.base_url).rstrip("/")
        def _enviar():
            enviar_nova_conta(
                destinatario  = empresa.email,
                nome_empresa  = empresa.razao_social,
                descricao     = dados.descricao + (" (recorrente)" if dados.recorrente else ""),
                valor         = dados.valor,
                vencimento    = dados.vencimento,
                codigo_barras = dados.codigo_barras,
                base_url      = base,
            )
        threading.Thread(target=_enviar, daemon=True).start()

    return {"id": rec_id, "parcelas": parcelas, "ok": True}


@router.patch("/contas-pagar/{conta_id}/pagar")
def marcar_pago(
    conta_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    conta = db.query(ContaPagar).filter(ContaPagar.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    verificar_acesso_empresa(usuario, conta.empresa_id, db)

    conta.pago = True
    db.commit()
    return {"ok": True}


@router.patch("/contas-pagar/{conta_id}/comprovante")
def registrar_comprovante(
    conta_id:       int,
    comprovante_url: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    """Cliente informa URL do comprovante e marca a conta como paga."""
    conta = db.query(ContaPagar).filter(ContaPagar.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    verificar_acesso_empresa(usuario, conta.empresa_id, db)
    conta.comprovante_url = comprovante_url
    conta.pago = True
    db.commit()
    return {"ok": True}


@router.delete("/contas-pagar/{conta_id}")
def deletar_conta(
    conta_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    """Remove permanentemente uma conta a pagar."""
    conta = db.query(ContaPagar).filter(ContaPagar.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    verificar_acesso_empresa(usuario, conta.empresa_id, db)

    db.delete(conta)
    db.commit()
    return {"ok": True}


# ── DRE ───────────────────────────────────────────────────────────────────────
@router.get("/dre/{empresa_id}")
def get_dre(
    empresa_id: int,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)

    hoje = datetime.today()
    mes  = mes or hoje.month
    ano  = ano or hoje.year

    q = db.query(Lancamento).filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.status     == StatusLancamento.confirmado,
    )
    lancamentos = filtro_mes_ano(q, Lancamento, mes, ano).all()

    receitas = [l for l in lancamentos if l.tipo == TipoLancamento.receita]
    despesas = [l for l in lancamentos if l.tipo == TipoLancamento.despesa]

    grp_rec  = {}
    for l in receitas:
        grp_rec[l.categoria] = grp_rec.get(l.categoria, 0) + l.valor

    grp_desp = {}
    for l in despesas:
        grp_desp[l.categoria] = grp_desp.get(l.categoria, 0) + l.valor

    total_rec  = sum(grp_rec.values())
    total_desp = sum(grp_desp.values())

    return {
        "mes":            mes,
        "ano":            ano,
        "receitas":       [{"categoria": k, "valor": v} for k, v in grp_rec.items()],
        "despesas":       [{"categoria": k, "valor": v} for k, v in grp_desp.items()],
        "total_receitas": total_rec,
        "total_despesas": total_desp,
        "resultado":      total_rec - total_desp,
    }
