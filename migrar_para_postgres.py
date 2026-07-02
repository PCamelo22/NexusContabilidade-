"""
Migração: SQLite (nexuscont.db) → PostgreSQL (Render)

Como usar:
  1. Instale o driver:  pip install psycopg2-binary
  2. Cole a External Database URL do Render abaixo (ou passe como argumento)
  3. Execute:  python migrar_para_postgres.py
"""

import sys
import os

# ── Cole aqui a External Database URL do Render ───────────────────────────────
POSTGRES_URL = os.getenv("DATABASE_URL") or "postgresql://usuario:senha@host/banco"

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "backend", "nexuscont.db")

# ─────────────────────────────────────────────────────────────────────────────

import sqlite3
import psycopg2
from psycopg2.extras import execute_values

def conectar_sqlite():
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ Banco SQLite não encontrado: {SQLITE_PATH}")
        sys.exit(1)
    return sqlite3.connect(SQLITE_PATH)

def conectar_postgres():
    try:
        return psycopg2.connect(POSTGRES_URL)
    except Exception as e:
        print(f"❌ Erro ao conectar no PostgreSQL: {e}")
        print("   Verifique a POSTGRES_URL no topo do script.")
        sys.exit(1)

def migrar():
    print("🔌 Conectando ao SQLite...")
    sqlite = conectar_sqlite()
    sqlite.row_factory = sqlite3.Row
    sc = sqlite.cursor()

    print("🔌 Conectando ao PostgreSQL...")
    pg = conectar_postgres()
    pc = pg.cursor()

    try:
        # ── 1. Usuários (contadores) ──────────────────────────────────────────
        sc.execute("SELECT * FROM usuarios ORDER BY id")
        usuarios = sc.fetchall()
        print(f"  → {len(usuarios)} usuário(s)")

        if usuarios:
            execute_values(pc, """
                INSERT INTO usuarios (id, nome, email, senha_hash, tipo, ativo, aprovado, criado_em)
                VALUES %s ON CONFLICT (id) DO NOTHING
            """, [(
                r["id"], r["nome"], r["email"], r["senha_hash"],
                r["tipo"], bool(r["ativo"]),
                bool(r["aprovado"]) if "aprovado" in r.keys() else True,
                r["criado_em"]
            ) for r in usuarios])

        # ── 2. Empresas (clientes) ────────────────────────────────────────────
        sc.execute("SELECT * FROM empresas ORDER BY id")
        empresas = sc.fetchall()
        print(f"  → {len(empresas)} empresa(s)")

        if empresas:
            execute_values(pc, """
                INSERT INTO empresas (id, razao_social, nome_fantasia, cnpj, email, senha_hash,
                    telefone, cep, cidade, endereco, ativo, criado_em, contador_id)
                VALUES %s ON CONFLICT (id) DO NOTHING
            """, [(
                r["id"], r["razao_social"], r["nome_fantasia"], r["cnpj"],
                r["email"], r["senha_hash"], r["telefone"],
                r["cep"] if "cep" in r.keys() else None,
                r["cidade"],
                r["endereco"] if "endereco" in r.keys() else None,
                bool(r["ativo"]), r["criado_em"], r["contador_id"]
            ) for r in empresas])

        # ── 3. Lançamentos ────────────────────────────────────────────────────
        sc.execute("SELECT * FROM lancamentos ORDER BY id")
        lancamentos = sc.fetchall()
        print(f"  → {len(lancamentos)} lançamento(s)")

        if lancamentos:
            execute_values(pc, """
                INSERT INTO lancamentos (id, empresa_id, data, descricao, categoria, tipo,
                    valor, status, origem, observacao, criado_em, criado_por)
                VALUES %s ON CONFLICT (id) DO NOTHING
            """, [(
                r["id"], r["empresa_id"], r["data"], r["descricao"],
                r["categoria"], r["tipo"], r["valor"], r["status"],
                r["origem"] if "origem" in r.keys() else "manual",
                r["observacao"], r["criado_em"],
                r["criado_por"] if "criado_por" in r.keys() else None
            ) for r in lancamentos])

        # ── 4. Contas a pagar ─────────────────────────────────────────────────
        sc.execute("SELECT * FROM contas_pagar ORDER BY id")
        contas = sc.fetchall()
        print(f"  → {len(contas)} conta(s) a pagar")

        if contas:
            execute_values(pc, """
                INSERT INTO contas_pagar (id, empresa_id, descricao, valor, vencimento,
                    categoria, codigo_barras, arquivo_url, comprovante_url,
                    pago, recorrente, frequencia, recorrencia_id, criado_em, criado_por)
                VALUES %s ON CONFLICT (id) DO NOTHING
            """, [(
                r["id"], r["empresa_id"], r["descricao"], r["valor"],
                r["vencimento"], r["categoria"],
                r["codigo_barras"] if "codigo_barras" in r.keys() else None,
                r["arquivo_url"] if "arquivo_url" in r.keys() else None,
                r["comprovante_url"] if "comprovante_url" in r.keys() else None,
                bool(r["pago"]), bool(r["recorrente"]),
                r["frequencia"] if "frequencia" in r.keys() else None,
                r["recorrencia_id"] if "recorrencia_id" in r.keys() else None,
                r["criado_em"],
                r["criado_por"] if "criado_por" in r.keys() else None
            ) for r in contas])

        # ── Atualizar sequences do PostgreSQL ─────────────────────────────────
        for tabela, seq in [
            ("usuarios",    "usuarios_id_seq"),
            ("empresas",    "empresas_id_seq"),
            ("lancamentos", "lancamentos_id_seq"),
            ("contas_pagar","contas_pagar_id_seq"),
        ]:
            pc.execute(f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {tabela}), 1))")

        pg.commit()
        print("\n✅ Migração concluída com sucesso!")

    except Exception as e:
        pg.rollback()
        print(f"\n❌ Erro durante a migração: {e}")
        import traceback; traceback.print_exc()
    finally:
        sqlite.close()
        pg.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        POSTGRES_URL = sys.argv[1]
    print(f"\n🚀 Iniciando migração SQLite → PostgreSQL")
    print(f"   SQLite : {SQLITE_PATH}")
    print(f"   Postgres: {POSTGRES_URL[:40]}...\n")
    migrar()
