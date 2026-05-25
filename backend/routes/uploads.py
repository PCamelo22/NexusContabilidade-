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
from limiter import limiter

router = APIRouter(prefix="/uploads", tags=["uploads"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── Magic bytes para validação real de tipo de arquivo ────────────────────────
_MAGIC = {
    "xlsx": b"PK\x03\x04",           # ZIP (OOXML)
    "xls":  b"\xd0\xcf\x11\xe0",     # OLE2 Compound
    "pdf":  b"%PDF",
}

def _validar_magic(conteudo: bytes, extensao: str) -> bool:
    """Verifica se os bytes iniciais batem com o tipo esperado."""
    ext = extensao.lstrip(".").lower()
    if ext == "csv":
        # CSV é texto puro — aceita se não começa com bytes de arquivo binário
        return conteudo[:3] not in (b"\xd0\xcf\x11", b"PK\x03\x04", b"%PDF")
    assinatura = _MAGIC.get(ext)
    if not assinatura:
        return False
    return conteudo[:len(assinatura)] == assinatura

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


def _normalizar(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def encontrar_coluna(df, *palavras_chave):
    """
    Encontra coluna pelo nome aproximado.
    Prioridade: primeira palavra-chave tem precedência sobre as demais.
    Ignora acentos e maiúsculas/minúsculas.
    """
    colunas_norm = {col: _normalizar(col) for col in df.columns}
    for kw in palavras_chave:
        kw_norm = _normalizar(kw)
        for col, col_norm in colunas_norm.items():
            if kw_norm in col_norm:
                return col
    return None


def detectar_colunas(df):
    """
    Detecta colunas para os formatos mais comuns de planilhas financeiras.
    Retorna dict com: data, desc, valor, credito, debito, tipo, categoria

    Formatos suportados:
      - Planilha de vendas (Data, Produto, Receita R$)
      - Extrato bancário (Data, Histórico, Crédito, Débito)
      - Contabilidade (Competência, Descrição, Tipo, Valor)
      - ERP/sistema (DT_LANCAMENTO, HISTORICO, NATUREZA, VLR_BRUTO)
      - OFX/CSV exportado (DTPOSTED, MEMO, TRNAMT)
      - Notas fiscais (Emissão, Fornecedor, Valor Fatura)
      - Planilha simples (Data, Descrição, Saída / Entrada)
    """
    cols = {c: None for c in ["data", "desc", "valor", "credito", "debito", "tipo", "categoria"]}

    cols["data"] = encontrar_coluna(df,
        "data", "date", "dtpost", "dt_", "_dt", "dt",
        "competencia", "vencimento", "emissao", "lancamento",
        "periodo", "dia", "mes",
    )
    cols["desc"] = encontrar_coluna(df,
        "descri", "historic", "memo", "detalhe", "observ",
        "produto", "item", "nome", "servico",
        "operacao", "lancamento", "complemento",
        "referencia", "narrat", "fornecedor", "cliente",
        "estabelec", "favorecido", "beneficiar",
    )
    cols["valor"] = encontrar_coluna(df,
        # Mais específicos primeiro
        "receita", "despesa",
        "credito", "debito",
        "entrada", "saida",
        # Genéricos
        "valor", "value", "amount", "amt", "trnamt",
        "quantia", "montante", "importancia",
        "total", "fatura", "venda",
        # ERP / sistemas internos
        "vlr", "vl_", "_vlr", "bruto", "liquido", "liq",
        "preco",
    )
    # Extratos bancários: colunas separadas de crédito e débito
    cols["credito"] = encontrar_coluna(df,
        "credito", "credit", "entrada", "receita",
    )
    cols["debito"] = encontrar_coluna(df,
        "debito", "debit", "saida", "despesa",
    )
    cols["tipo"] = encontrar_coluna(df,
        "tipo", "type", "natureza", "dc", "d/c", "debcred",
        "moviment", "operacao", "trntype",
    )
    cols["categoria"] = encontrar_coluna(df,
        "categor", "classif", "grupo", "subgrupo",
        "conta", "plano", "centro", "subcategor",
    )
    return cols


# ── Upload Excel ──────────────────────────────────────────────────────────────
@router.post("/excel/{empresa_id}")
@limiter.limit("20/minute")
async def upload_excel(
    request: Request,
    empresa_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)

    # Valida extensão permitida
    ext = os.path.splitext(arquivo.filename or "")[1].lower()
    if ext not in (".xlsx", ".xls", ".csv"):
        raise HTTPException(status_code=400, detail="Formato inválido. Envie .xlsx, .xls ou .csv")

    conteudo = await arquivo.read()
    if len(conteudo) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Arquivo maior que {MAX_UPLOAD_MB}MB")

    # Valida magic bytes (bloqueia arquivos renomeados)
    if not _validar_magic(conteudo, ext):
        raise HTTPException(
            status_code=400,
            detail="O arquivo não corresponde ao formato declarado. Envie um arquivo Excel ou CSV genuíno."
        )

    try:
        # Lê CSV (tenta UTF-8, depois latin-1) ou Excel
        if arquivo.filename.lower().endswith(".csv"):
            try:
                df = pd.read_csv(io.BytesIO(conteudo), encoding="utf-8", sep=None, engine="python")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(conteudo), encoding="latin-1", sep=None, engine="python")
        else:
            df = pd.read_excel(io.BytesIO(conteudo))

        df.columns = [str(c).strip() for c in df.columns]
        # Remove linhas completamente vazias
        df = df.dropna(how="all")

        cols = detectar_colunas(df)

        # Modo extrato bancário: colunas separadas e distintas de crédito e débito
        modo_extrato = bool(
            cols["credito"] and cols["debito"]
            and cols["credito"] != cols["debito"]
            and cols["credito"] != cols["valor"]
            and cols["debito"]  != cols["valor"]
        )

        if not cols["data"]:
            raise HTTPException(
                status_code=400,
                detail=f"Não foi possível identificar a coluna de data. "
                       f"Colunas encontradas: {', '.join(df.columns.tolist())}"
            )
        if not cols["valor"] and not modo_extrato:
            raise HTTPException(
                status_code=400,
                detail=f"Não foi possível identificar a coluna de valor. "
                       f"Colunas encontradas: {', '.join(df.columns.tolist())}"
            )

        # Tipo fixo deduzido pelo nome da coluna de valor (normalizado, sem acentos)
        tipo_fixo = None
        if cols["valor"] and not modo_extrato:
            nome_col = _normalizar(cols["valor"])
            if any(p in nome_col for p in ["receita", "entrada", "venda", "credito", "credit"]):
                tipo_fixo = "receita"
            elif any(p in nome_col for p in ["despesa", "saida", "debito", "debit", "custo"]):
                tipo_fixo = "despesa"

        lancamentos = []
        erros = 0

        for _, row in df.iterrows():
            try:
                data = limpar_data(row[cols["data"]])

                # ── Modo extrato: processa crédito e débito como linhas separadas
                if modo_extrato:
                    val_cred = limpar_valor(row[cols["credito"]])
                    val_deb  = limpar_valor(row[cols["debito"]])
                    desc     = str(row[cols["desc"]]).strip() if cols["desc"] else "Importado via Excel"
                    cat_val  = str(row[cols["categoria"]]).strip() if cols["categoria"] else None

                    if val_cred > 0:
                        lancamentos.append(Lancamento(
                            empresa_id=empresa_id, data=data,
                            descricao=desc[:200],
                            categoria=cat_val or "Outras Receitas",
                            tipo="receita", valor=val_cred,
                            status=StatusLancamento.pendente,
                            origem="excel", criado_por=int(usuario["sub"]),
                        ))
                    if val_deb > 0:
                        lancamentos.append(Lancamento(
                            empresa_id=empresa_id, data=data,
                            descricao=desc[:200],
                            categoria=cat_val or "Outras Despesas",
                            tipo="despesa", valor=val_deb,
                            status=StatusLancamento.pendente,
                            origem="excel", criado_por=int(usuario["sub"]),
                        ))
                    continue

                # ── Modo padrão: uma coluna de valor
                valor = limpar_valor(row[cols["valor"]])
                if valor == 0:
                    continue

                # Determina tipo
                if tipo_fixo:
                    tipo = tipo_fixo
                elif cols["tipo"]:
                    tipo_raw = str(row[cols["tipo"]]).strip().lower()
                    DESPESA_KW = ["d", "deb", "debit", "debito", "débito",
                                  "saida", "saída", "despesa", "c/d", "s"]
                    RECEITA_KW = ["c", "cred", "credit", "credito", "crédito",
                                  "entrada", "receita", "c/c", "e"]
                    if tipo_raw in DESPESA_KW or any(p in tipo_raw for p in ["despesa", "saida", "debit"]):
                        tipo = "despesa"
                    elif tipo_raw in RECEITA_KW or any(p in tipo_raw for p in ["receita", "entrada", "credit"]):
                        tipo = "receita"
                    else:
                        tipo = detectar_tipo(row[cols["valor"]])
                else:
                    tipo = detectar_tipo(row[cols["valor"]])

                desc = str(row[cols["desc"]]).strip() if cols["desc"] else "Importado via Excel"
                if not desc or desc in ("nan", "None", ""):
                    desc = "Importado via Excel"

                cat_val = str(row[cols["categoria"]]).strip() if cols["categoria"] else None
                if not cat_val or cat_val in ("nan", "None", ""):
                    cat_val = "Outras Receitas" if tipo == "receita" else "Outras Despesas"

                lancamentos.append(Lancamento(
                    empresa_id = empresa_id,
                    data       = data,
                    descricao  = desc[:200],
                    categoria  = cat_val,
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
@limiter.limit("20/minute")
async def upload_pdf(
    request: Request,
    empresa_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual)
):
    verificar_acesso_empresa(usuario, empresa_id, db)  # ← verifica ownership

    # Valida extensão
    ext = os.path.splitext(arquivo.filename or "")[1].lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Formato inválido. Envie um arquivo .pdf")

    conteudo = await arquivo.read()
    if len(conteudo) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Arquivo maior que {MAX_UPLOAD_MB}MB")

    # Valida magic bytes
    if not _validar_magic(conteudo, "pdf"):
        raise HTTPException(
            status_code=400,
            detail="O arquivo não é um PDF válido. Verifique o arquivo e tente novamente."
        )

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
@limiter.limit("20/minute")
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
@limiter.limit("20/minute")
async def upload_comprovante(
    request:  Request,
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
