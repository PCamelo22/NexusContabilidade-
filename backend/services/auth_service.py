# auth_service.py — Nexus v1.0


from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models import Usuario, Empresa, TipoUsuario
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
    contador = db.query(Usuario).filter(Usuario.email == "contadora@elaconta.com.br").first()
    if not contador:
        contador = Usuario(
            nome       = "Ana Paula Silva",
            email      = "contadora@elaconta.com.br",
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
    for e in empresas_teste:
        if not db.query(Empresa).filter(Empresa.email == e["email"]).first():
            db.add(Empresa(
                razao_social  = e["razao_social"],
                nome_fantasia = e["nome_fantasia"],
                cnpj          = e["cnpj"],
                email         = e["email"],
                senha_hash    = hash_senha("123456"),
                telefone      = e["telefone"],
                cidade        = e["cidade"],
                contador_id   = contador.id,
            ))

    db.commit()