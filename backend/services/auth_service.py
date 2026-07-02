# auth_service.py — Nexus v1.0


import random
from datetime import datetime, timedelta, date
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models import Usuario, Empresa, TipoUsuario, Lancamento, ContaPagar, TipoLancamento, StatusLancamento
from config import SECRET_KEY, ALGORITHM, TOKEN_EXPIRY

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Senha ─────────────────────────────────────────────────────────────────────
def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


# ── Token JWT ─────────────────────────────────────────────────────────────────
def criar_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRY)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── Autenticação ──────────────────────────────────────────────────────────────
def autenticar_usuario(db: Session, email: str, senha: str):
    """Tenta autenticar como contador primeiro, depois como empresa (cliente)."""

    # Tenta como contador
    usuario = db.query(Usuario).filter(
        Usuario.email == email,
        Usuario.ativo == True
    ).first()

    if usuario and verificar_senha(senha, usuario.senha_hash):
        return {
            "id":       usuario.id,
            "nome":     usuario.nome,
            "email":    usuario.email,
            "tipo":     usuario.tipo.value,
            "aprovado": bool(usuario.aprovado),
        }

    # Tenta como empresa (cliente)
    empresa = db.query(Empresa).filter(
        Empresa.email == email,
        Empresa.ativo == True
    ).first()

    if empresa and verificar_senha(senha, empresa.senha_hash):
        return {
            "id":    empresa.id,
            "nome":  empresa.razao_social,
            "email": empresa.email,
            "tipo":  "cliente",
        }

    return None


# ── Seed — cria dados iniciais ────────────────────────────────────────────────
def seed(db: Session):
    """Cria contadora e empresa de teste se não existirem."""

    # Contadora padrão — flush para obter o ID antes de criar a empresa
    contador = db.query(Usuario).filter(Usuario.email == "contador@nexuscontabilidade.com.br").first()
    if not contador:
        contador = Usuario(
            nome       = "Nexus",
            email      = "contador@nexuscontabilidade.com.br",
            senha_hash = hash_senha("123456"),
            tipo       = TipoUsuario.contador,
            aprovado   = True,
        )
        db.add(contador)
        db.flush()   # garante que contador.id já está disponível

    empresas_teste = [
        dict(razao_social="Mercado Silva Ltda",          nome_fantasia="Mercado Silva",        cnpj="12.345.678/0001-99", email="cliente@mercadosilva.com.br",      telefone="(61) 99100-0001", cidade="Brasília"),
        dict(razao_social="Tech Inovações Ltda",         nome_fantasia="Tech Inovações",       cnpj="23.456.789/0001-10", email="financeiro@techinov.com.br",        telefone="(11) 99200-0002", cidade="São Paulo"),
        dict(razao_social="Restaurante Bom Sabor ME",    nome_fantasia="Bom Sabor",            cnpj="34.567.890/0001-21", email="contato@bomsabor.com.br",           telefone="(21) 99300-0003", cidade="Rio de Janeiro"),
        dict(razao_social="Lima & Associados Advocacia", nome_fantasia="Lima Advocacia",       cnpj="45.678.901/0001-32", email="admin@limaadvocacia.com.br",         telefone="(61) 99400-0004", cidade="Brasília"),
        dict(razao_social="Construções BH Ltda",         nome_fantasia="Construções BH",       cnpj="56.789.012/0001-43", email="financeiro@construcoesbh.com.br",   telefone="(31) 99500-0005", cidade="Belo Horizonte"),
        dict(razao_social="Farmácia Central ME",         nome_fantasia="Farmácia Central",     cnpj="67.890.123/0001-54", email="caixa@farmaciacentral.com.br",       telefone="(41) 99600-0006", cidade="Curitiba"),
        dict(razao_social="Academia Fitness Plus Ltda",  nome_fantasia="Fitness Plus",         cnpj="78.901.234/0001-65", email="admin@fitnessplus.com.br",           telefone="(51) 99700-0007", cidade="Porto Alegre"),
        dict(razao_social="Transporte Expresso Ltda",    nome_fantasia="Transporte Expresso",  cnpj="89.012.345/0001-76", email="financeiro@transpexpresso.com.br",   telefone="(71) 99800-0008", cidade="Salvador"),
    ]
    empresas_criadas = []
    for e in empresas_teste:
        emp = db.query(Empresa).filter(Empresa.email == e["email"]).first()
        if not emp:
            emp = Empresa(
                razao_social  = e["razao_social"],
                nome_fantasia = e["nome_fantasia"],
                cnpj          = e["cnpj"],
                email         = e["email"],
                senha_hash    = hash_senha("123456"),
                telefone      = e["telefone"],
                cidade        = e["cidade"],
                contador_id   = contador.id,
            )
            db.add(emp)
            db.flush()
            empresas_criadas.append(emp)

    db.flush()

    # ── Dados de demonstração por segmento ───────────────────────────────────
    perfis = {
        "cliente@mercadosilva.com.br": {
            "receitas": [("Venda no balcão", "Vendas", 4800), ("Venda delivery", "Vendas", 2200), ("Venda atacado", "Vendas", 6500)],
            "despesas": [("Aluguel loja", "Aluguel", 2800), ("Fornecedor alimentar", "Fornecedores", 3200), ("Energia elétrica", "Utilidades", 580), ("Folha de pagamento", "Pessoal", 4200)],
            "contas": [("Aluguel", 2800, "Aluguel"), ("Fornecedor principal", 3200, "Fornecedores"), ("Seguro loja", 420, "Seguros")],
        },
        "financeiro@techinov.com.br": {
            "receitas": [("Projeto de software", "Serviços", 12000), ("Manutenção mensal", "Serviços", 4500), ("Consultoria TI", "Serviços", 8000)],
            "despesas": [("Aluguel escritório", "Aluguel", 3500), ("Licenças de software", "TI", 1200), ("Folha de pagamento", "Pessoal", 8500), ("Marketing digital", "Marketing", 1800)],
            "contas": [("Aluguel escritório", 3500, "Aluguel"), ("Licenças AWS", 1200, "TI"), ("Plano de saúde", 2400, "Benefícios")],
        },
        "contato@bomsabor.com.br": {
            "receitas": [("Vendas salão", "Vendas", 9500), ("Eventos e buffet", "Eventos", 3800), ("Delivery", "Vendas", 2400)],
            "despesas": [("Insumos cozinha", "Fornecedores", 4200), ("Aluguel", "Aluguel", 3200), ("Pessoal", "Pessoal", 5500), ("Gás e energia", "Utilidades", 680)],
            "contas": [("Aluguel restaurante", 3200, "Aluguel"), ("Fornecedor bebidas", 1800, "Fornecedores"), ("Alvará funcionamento", 650, "Taxas")],
        },
        "admin@limaadvocacia.com.br": {
            "receitas": [("Honorários advocatícios", "Serviços", 15000), ("Consultoria jurídica", "Serviços", 6000), ("Parecer jurídico", "Serviços", 3500)],
            "despesas": [("Aluguel sala", "Aluguel", 4200), ("OAB anuidade", "Taxas", 800), ("Pessoal administrativo", "Pessoal", 3800), ("Material escritório", "Suprimentos", 350)],
            "contas": [("Aluguel sala", 4200, "Aluguel"), ("Assinatura jurídica", 980, "Assinaturas"), ("IPTU proporcional", 1200, "Impostos")],
        },
        "financeiro@construcoesbh.com.br": {
            "receitas": [("Obra residencial", "Serviços", 25000), ("Reforma comercial", "Serviços", 18000), ("Manutenção predial", "Serviços", 7500)],
            "despesas": [("Material de construção", "Materiais", 12000), ("Mão de obra", "Pessoal", 9500), ("Equipamentos", "Equipamentos", 3200), ("Combustível", "Veículos", 1800)],
            "contas": [("Financiamento equipamento", 4500, "Financiamentos"), ("Seguro obras", 1200, "Seguros"), ("Aluguel depósito", 2200, "Aluguel")],
        },
        "caixa@farmaciacentral.com.br": {
            "receitas": [("Venda medicamentos", "Vendas", 18000), ("Venda cosméticos", "Vendas", 4200), ("Manipulação", "Serviços", 3500)],
            "despesas": [("Distribuidora medicamentos", "Fornecedores", 9500), ("Aluguel ponto", "Aluguel", 3800), ("Pessoal", "Pessoal", 5200), ("Energia", "Utilidades", 420)],
            "contas": [("Distribuidora Farma", 9500, "Fornecedores"), ("Aluguel ponto", 3800, "Aluguel"), ("CRF anuidade", 480, "Taxas")],
        },
        "admin@fitnessplus.com.br": {
            "receitas": [("Mensalidades alunos", "Mensalidades", 22000), ("Plano anual", "Mensalidades", 8500), ("Personal trainer", "Serviços", 4200)],
            "despesas": [("Aluguel academia", "Aluguel", 6500), ("Pessoal", "Pessoal", 7800), ("Manutenção equipamentos", "Manutenção", 1200), ("Energia elétrica", "Utilidades", 1800)],
            "contas": [("Aluguel academia", 6500, "Aluguel"), ("Manutenção equipamentos", 1200, "Manutenção"), ("Sistema de gestão", 380, "TI")],
        },
        "financeiro@transpexpresso.com.br": {
            "receitas": [("Frete carga geral", "Serviços", 32000), ("Frete refrigerado", "Serviços", 15000), ("Logística reversa", "Serviços", 8000)],
            "despesas": [("Combustível frota", "Veículos", 18000), ("Manutenção caminhões", "Veículos", 5500), ("Pessoal motoristas", "Pessoal", 12000), ("Seguro frota", "Seguros", 3200)],
            "contas": [("Financiamento caminhão", 8500, "Financiamentos"), ("Seguro frota", 3200, "Seguros"), ("IPVA frota", 2800, "Impostos")],
        },
    }

    rng = random.Random(42)
    hoje = date.today()

    for emp in empresas_criadas:
        perfil = perfis.get(emp.email)
        if not perfil:
            continue

        tem_lancamentos = db.query(Lancamento).filter(Lancamento.empresa_id == emp.id).first()
        if tem_lancamentos:
            continue

        # Gera lançamentos para os últimos 6 meses
        for meses_atras in range(5, -1, -1):
            primeiro = (hoje.replace(day=1) - timedelta(days=meses_atras * 30)).replace(day=1)
            ultimo_dia = (primeiro.replace(month=primeiro.month % 12 + 1, day=1) - timedelta(days=1)).day if primeiro.month < 12 else 31

            # 3-5 receitas por mês
            for desc, cat, base in rng.choices(perfil["receitas"], k=rng.randint(3, 5)):
                dia = rng.randint(1, min(ultimo_dia, 28))
                valor = round(base * rng.uniform(0.85, 1.18), 2)
                db.add(Lancamento(
                    empresa_id = emp.id,
                    data       = primeiro.replace(day=dia).isoformat(),
                    descricao  = desc,
                    categoria  = cat,
                    tipo       = TipoLancamento.receita,
                    valor      = valor,
                    status     = StatusLancamento.confirmado,
                    criado_por = contador.id,
                ))

            # 3-5 despesas por mês
            for desc, cat, base in rng.choices(perfil["despesas"], k=rng.randint(3, 5)):
                dia = rng.randint(1, min(ultimo_dia, 28))
                valor = round(base * rng.uniform(0.90, 1.10), 2)
                db.add(Lancamento(
                    empresa_id = emp.id,
                    data       = primeiro.replace(day=dia).isoformat(),
                    descricao  = desc,
                    categoria  = cat,
                    tipo       = TipoLancamento.despesa,
                    valor      = valor,
                    status     = StatusLancamento.confirmado,
                    criado_por = contador.id,
                ))

        # Contas a pagar
        tem_contas = db.query(ContaPagar).filter(ContaPagar.empresa_id == emp.id).first()
        if not tem_contas:
            for i, (desc, valor, cat) in enumerate(perfil["contas"]):
                venc = hoje + timedelta(days=rng.randint(3, 25) + i * 7)
                db.add(ContaPagar(
                    empresa_id = emp.id,
                    descricao  = desc,
                    valor      = round(valor * rng.uniform(0.95, 1.05), 2),
                    vencimento = venc.isoformat(),
                    categoria  = cat,
                    pago       = False,
                    recorrente = True,
                    frequencia = "mensal",
                    criado_por = contador.id,
                ))

    db.commit()