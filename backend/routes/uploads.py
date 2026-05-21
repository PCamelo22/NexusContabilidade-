# routes/uploads.py — ElaConta v1.0

import os
import io
import uuid
import threading
import pandas as pd
import pdfplumber
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from database import get_db
from models import Lancamento, Empresa, ContaPagar, StatusLancamento
from services.auth_service import decodificar_token
from services.email_service import enviar_boleto_disponivel
from fastapi.security import OAuth2PasswordBearer
from config import UPLOAD_DIR, MAX_UPLOAD_MB

router = APIRouter(prefix="/uploads", tags=["uploads"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_usuario_atual(token: str = Depends(oauth2)):
    payload = decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    return payload


def verificar_acesso_empresa(usuario: dict, empresa_id: int, db: Session):
    """Somente contador dono da empresa pode fazer upload."""
    if usuario["tipo"] != "contador":
        raise HTTPException(status_code=403, detail="Apenas contadores podem importar dados")
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if empresa.contador_id != int(usuario["sub"]):
        raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")


def detectar_tipo(valor_str: str) -> str:
    """Detecta se é receita ou despesa pelo sinal do valor."""
    try:
        v = float(str(valor_str).replace("R$", "").replace(".", "").replace(",", ".").strip())
        return "receita" if v > 0 else "despesa"
    except:
        return "despesa"


def limpar_valor(valor_str: str) -> float:
    """Converte string de valor para float positivo."""
    try:
        v = str(valor_str).replace("R$", "").replace(".", "").replace(",", ".").strip()
        return abs(float(v))
    except:
        return 0.0


def limpar_data(data_str: str) -> str:
    """Converte data para YYYY-MM-DD."""
    from datetime import datetime
    formatos = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"]
    for fmt in formatos:
        try:
            return datetime.strptime(str(data_str).strip(), fmt).strftime("%Y-%m-%d")
        except:
            continue
    return str(data_str)


def encontrar_coluna(df, *palavras_chave):
    """Encontra coluna pelo nome aproximado."""
    for col in df.columns:
        for kw in palavras_chave:
            if kw.lower() in str(col).lower():
                return col
    return None


# ── Upload Excel ──────────────────────────────────────────────────────────────
@router.post("/excel/{empresa_id}")
async def upload_excel(
    empresa_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)  # ← verifica ownership

    conteudo = await arquivo.read()
    if len(conteudo) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Arquivo maior que {MAX_UPLOAD_MB}MB")

    try:
        if arquivo.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(conteudo), encoding="utf-8", sep=None, engine="python")
        else:
            df = pd.read_excel(io.BytesIO(conteudo))

        df.columns = [str(c).strip() for c in df.columns]

        col_data      = encontrar_coluna(df, "data", "date", "dt")
        col_desc      = encontrar_coluna(df, "descri", "historic", "memo", "detalhe")
        col_valor     = encontrar_coluna(df, "valor", "value", "amount", "quantia")
        col_tipo      = encontrar_coluna(df, "tipo", "type", "natureza")
        col_categoria = encontrar_coluna(df, "categor", "classif")

        if not col_data or not col_valor:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível identificar as colunas de data e valor. Verifique o arquivo."
            )

        lancamentos = []
        erros = 0

        for _, row in df.iterrows():
            try:
                data  = limpar_data(row[col_data])
                valor = limpar_valor(row[col_valor])
                if valor == 0:
                    continue

                tipo = "receita"
                if col_tipo:
                    tipo_raw = str(row[col_tipo]).lower()
                    if any(p in tipo_raw for p in ["debit", "saida", "saída", "despesa", "d"]):
                        tipo = "despesa"
                    elif any(p in tipo_raw for p in ["credit", "entrada", "receita", "c"]):
                        tipo = "receita"
                else:
                    tipo = detectar_tipo(row[col_valor])

                desc      = str(row[col_desc]).strip() if col_desc else "Importado via Excel"
                categoria = str(row[col_categoria]).strip() if col_categoria else (
                    "Outras Receitas" if tipo == "receita" else "Outras Despesas"
                )

                lancamentos.append(Lancamento(
                    empresa_id = empresa_id,
                    data       = data,
                    descricao  = desc[:200],
                    categoria  = categoria,
                    tipo       = tipo,
                    valor      = valor,
                    status     = StatusLancamento.pendente,
                    origem     = "excel",
                    criado_por = int(usuario["sub"]),
                ))
            except:
                erros += 1
                continue

        db.bulk_save_objects(lancamentos)
        db.commit()

        return {
            "ok":         True,
            "importados": len(lancamentos),
            "erros":      erros,
            "mensagem":   f"{len(lancamentos)} lançamentos importados com status 'pendente'. Revise antes de confirmar."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")


# ── Upload PDF ────────────────────────────────────────────────────────────────
@router.post("/pdf/{empresa_id}")
async def upload_pdf(
    empresa_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)  # ← verifica ownership

    conteudo = await arquivo.read()
    if len(conteudo) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Arquivo maior que {MAX_UPLOAD_MB}MB")

    try:
        import re
        from datetime import datetime

        texto_total = ""
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            for page in pdf.pages:
                texto_total += (page.extract_text() or "") + "\n"

        if not texto_total.strip():
            raise HTTPException(status_code=400, detail="PDF não contém texto pesquisável")

        padrao = re.compile(
            r"(\d{2}/\d{2}/\d{4}|\d{2}/\d{2}/\d{2})"
            r"\s+"
            r"(.{5,80}?)"
            r"\s+"
            r"([-+]?\s*R?\$?\s*[\d.,]+)"
        )

        lancamentos = []
        for match in padrao.finditer(texto_total):
            try:
                data  = limpar_data(match.group(1))
                desc  = match.group(2).strip()
                valor = limpar_valor(match.group(3))
                if valor == 0:
                    continue
                tipo = detectar_tipo(match.group(3))
                lancamentos.append(Lancamento(
                    empresa_id = empresa_id,
                    data       = data,
                    descricao  = desc[:200],
                    categoria  = "Outras Receitas" if tipo == "receita" else "Outras Despesas",
                    tipo       = tipo,
                    valor      = valor,
                    status     = StatusLancamento.pendente,
                    origem     = "pdf",
                    criado_por = int(usuario["sub"]),
                ))
            except:
                continue

        db.bulk_save_objects(lancamentos)
        db.commit()

        return {
            "ok":         True,
            "importados": len(lancamentos),
            "mensagem":   f"{len(lancamentos)} lançamentos extraídos do PDF com status 'pendente'. Revise antes de confirmar."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")


# ── Upload Boleto (PDF da conta a pagar) ─────────────────────────────────────
@router.post("/boleto/{conta_id}")
async def upload_boleto(
    request:  Request,
    conta_id: int,
    arquivo:  UploadFile = File(...),
    db:       Session    = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    """Contadora faz upload do PDF do boleto para uma conta a pagar."""
    if usuario["tipo"] != "contador":
        raise HTTPException(status_code=403, detail="Apenas contadores podem anexar boletos")

    conta = db.query(ContaPagar).filter(ContaPagar.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # verifica que a empresa pertence a este contador
    empresa = db.query(Empresa).filter(Empresa.id == conta.empresa_id).first()
    if not empresa or empresa.contador_id != int(usuario["sub"]):
        raise HTTPException(status_code=403, detail="Acesso negado")

    conteudo = await arquivo.read()
    if len(conteudo) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Arquivo maior que {MAX_UPLOAD_MB}MB")

    # aceita PDF e imagens
    ext = os.path.splitext(arquivo.filename or "")[-1].lower()
    if ext not in [".pdf", ".png", ".jpg", ".jpeg"]:
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF ou imagem")

    nome_arquivo = f"boleto_{conta_id}_{uuid.uuid4().hex[:8]}{ext}"
    pasta        = os.path.join(UPLOAD_DIR, "boletos")
    os.makedirs(pasta, exist_ok=True)
    caminho      = os.path.join(pasta, nome_arquivo)

    with open(caminho, "wb") as f:
        f.write(conteudo)

    url = f"/uploads/boletos/{nome_arquivo}"
    conta.arquivo_url = url
    db.commit()

    # notifica o cliente por e-mail em background
    if empresa.email:
        base = str(request.base_url).rstrip("/")
        _conta = dict(descricao=conta.descricao, valor=conta.valor,
                      vencimento=conta.vencimento)
        def _enviar(e=empresa.email, n=empresa.razao_social,
                    c=_conta, u=url, b=base):
            enviar_boleto_disponivel(e, n, c["descricao"],
                                     c["valor"], c["vencimento"], u, b)
        threading.Thread(target=_enviar, daemon=True).start()

    return {"ok": True, "url": url}


# ── Upload Comprovante (cliente envia prova de pagamento) ─────────────────────
@router.post("/comprovante/{conta_id}")
async def upload_comprovante(
    conta_id: int,
    arquivo:  UploadFile = File(...),
    db:       Session    = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    """Cliente faz upload do comprovante e a conta é marcada como paga."""
    conta = db.query(ContaPagar).filter(ContaPagar.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # cliente só pode enviar comprovante da própria empresa
    if usuario["tipo"] == "cliente" and int(usuario["sub"]) != conta.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    conteudo = await arquivo.read()
    if len(conteudo) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Arquivo maior que {MAX_UPLOAD_MB}MB")

    ext = os.path.splitext(arquivo.filename or "")[-1].lower()
    if ext not in [".pdf", ".png", ".jpg", ".jpeg"]:
        raise HTTPException(status_code=400, detail="Envie um PDF ou imagem")

    nome_arquivo = f"comp_{conta_id}_{uuid.uuid4().hex[:8]}{ext}"
    pasta        = os.path.join(UPLOAD_DIR, "comprovantes")
    os.makedirs(pasta, exist_ok=True)
    caminho      = os.path.join(pasta, nome_arquivo)

    with open(caminho, "wb") as f:
        f.write(conteudo)

    url = f"/uploads/comprovantes/{nome_arquivo}"
    conta.comprovante_url = url
    conta.pago            = True
    db.commit()

    return {"ok": True, "url": url}


# ── Confirmar lançamentos pendentes ──────────────────────────────────────────
@router.patch("/confirmar/{empresa_id}")
def confirmar_pendentes(
    empresa_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)  # ← verifica ownership

    pendentes = db.query(Lancamento).filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.status     == StatusLancamento.pendente,
    ).all()

    for l in pendentes:
        l.status = StatusLancamento.confirmado

    db.commit()
    return {"ok": True, "confirmados": len(pendentes)}
