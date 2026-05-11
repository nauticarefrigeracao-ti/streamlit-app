"""Testes de integração — conexão e schema do banco de dados."""

import sqlite3

import pytest


class TestGetConnection:

    def test_retorna_conexao_valida(self, tmp_db):
        from src.db.connection import get_connection
        conn = get_connection()
        assert conn is not None
        conn.close()

    def test_wal_mode_ativo(self, tmp_db):
        from src.db.connection import get_connection
        conn = get_connection()
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_foreign_keys_ativo(self, tmp_db):
        from src.db.connection import get_connection
        conn = get_connection()
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()
        assert fk == 1

    def test_row_factory_e_sqlite_row(self, tmp_db):
        from src.db.connection import get_connection
        conn = get_connection()
        row = conn.execute("SELECT 1 AS val").fetchone()
        conn.close()
        assert row["val"] == 1  # acesso por nome — Row factory ativo

    def test_diretorio_criado_automaticamente(self, tmp_path, monkeypatch):
        nested = tmp_path / "sub" / "deep" / "test.db"
        monkeypatch.setattr("src.db.connection.DB_PATH", nested)
        from src.db.connection import get_connection
        conn = get_connection()
        conn.close()
        assert nested.exists()


class TestInitDb:

    def test_tabela_fato_vendas_criada(self, tmp_db):
        conn = sqlite3.connect(str(tmp_db))
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "fato_vendas" in tables

    def test_indice_periodo_criado(self, tmp_db):
        conn = sqlite3.connect(str(tmp_db))
        indexes = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        conn.close()
        assert "idx_fv_periodo" in indexes

    def test_indice_sku_criado(self, tmp_db):
        conn = sqlite3.connect(str(tmp_db))
        indexes = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        conn.close()
        assert "idx_fv_sku" in indexes

    def test_unique_constraint_existe(self, tmp_db):
        conn = sqlite3.connect(str(tmp_db))
        ddl = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='fato_vendas'"
        ).fetchone()[0]
        conn.close()
        assert "UNIQUE" in ddl.upper()

    def test_unique_constraint_rejeita_duplicata(self, tmp_db):
        conn = sqlite3.connect(str(tmp_db))
        row = ("2025-01-01", "arq.xls", "SKU-1", "Prod", 100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        cols = "data_referencia,fonte,sku,produto,receita_total,frete,comissao_ml,custo_produto,incentivo,imposto,total_liquido,margem"
        sql = f"INSERT INTO fato_vendas ({cols}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
        conn.execute(sql, row)
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, row)
        conn.close()

    def test_init_db_idempotente(self, tmp_db):
        """Chamar init_db duas vezes não deve levantar erro."""
        from src.db.schema import init_db
        init_db()
        init_db()

    def test_colunas_presentes(self, tmp_db):
        conn = sqlite3.connect(str(tmp_db))
        info = conn.execute("PRAGMA table_info(fato_vendas)").fetchall()
        conn.close()
        col_names = {r[1] for r in info}
        expected = {
            "id", "data_referencia", "fonte", "sku", "produto",
            "receita_total", "frete", "comissao_ml", "custo_produto",
            "incentivo", "imposto", "total_liquido", "margem", "data_ingestao",
        }
        assert expected.issubset(col_names)
