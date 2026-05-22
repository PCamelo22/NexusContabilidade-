# auth_service.py — ElaConta v1.0


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

    # Empresa de teste vinculada ao contador real (não mais hardcoded id=1)
    if not db.query(Empresa).filter(Empresa.email == "cliente@mercadosilva.com.br").first():
        db.add(Empresa(
            razao_social  = "Mercado Silva Ltda",
            nome_fantasia = "Mercado Silva",
            cnpj          = "12.345.678/0001-99",
            email         = "cliente@mercadosilva.com.br",
            senha_hash    = hash_senha("123456"),
            contador_id   = contador.id,
        ))

    db.commit()