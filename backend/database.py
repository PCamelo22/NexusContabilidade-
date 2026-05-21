# database.py — ElaConta v1.0

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

# SQLite exige check_same_thread=False
# PostgreSQL/Supabase usa pool_pre_ping para detectar conexões mortas
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrar_colunas():
    """Adiciona colunas novas sem derrubar tabelas existentes (SQLite-safe)."""
    if not DATABASE_URL.startswith("sqlite"):
        return  # MySQL/Postgres usa Alembic — não precisa disso
    import sqlite3, os
    db_path = DATABASE_URL.replace("sqlite:///", "").replace("./", "")
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    # Descobre colunas existentes em contas_pagar
    cur.execute("PRAGMA table_info(contas_pagar)")
    cols = {row[1] for row in cur.fetchall()}
    novas = [
        ("recorrente",     "INTEGER DEFAULT 0"),
        ("frequencia",     "TEXT"),
        ("recorrencia_id", "INTEGER"),
    ]
    for col, tipo in novas:
        if col not in cols:
            cur.execute(f"ALTER TABLE contas_pagar ADD COLUMN {col} {tipo}")
    conn.commit()
    conn.close()
