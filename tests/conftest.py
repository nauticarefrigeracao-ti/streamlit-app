"""Fixtures compartilhadas entre unit e integration tests."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest


# ── Fixture: banco de dados isolado em memória/tmp ────────────────────────────

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """DB SQLite isolado no tmp_path — nunca toca o banco de produção."""
    db = tmp_path / "test.db"
    monkeypatch.setattr("src.db.connection.DB_PATH", db)
    monkeypatch.setattr("src.config.DB_PATH", db)
    from src.db.schema import init_db
    init_db()
    return db


@pytest.fixture
def seeded_db(tmp_db):
    """DB com dados de dois períodos pré-inseridos para testes de query."""
    import sqlite3 as _sq
    rows = [
        # periodo 2025-01-01
        ("2025-01-01", "jan.xls", "SKU-A", "Produto Alpha",  1000.0,  50.0, 150.0, 300.0, 20.0, 255.9,  264.1, 0.2641),
        ("2025-01-01", "jan.xls", "SKU-B", "Produto Beta",    500.0,  30.0,  80.0, 200.0,  0.0, 127.95, 62.05, 0.1241),
        ("2025-01-01", "jan.xls", "SKU-C", "Produto Gamma",   200.0,  20.0,  40.0, 100.0,  0.0,  51.18, -11.18, -0.0559),
        # periodo 2025-02-01
        ("2025-02-01", "fev.xls", "SKU-A", "Produto Alpha",  1200.0,  60.0, 180.0, 310.0, 25.0, 306.96, 368.04, 0.3067),
        ("2025-02-01", "fev.xls", "SKU-B", "Produto Beta",    480.0,  25.0,  75.0, 190.0,  0.0, 122.83,  67.17, 0.1399),
        ("2025-02-01", "fev.xls", "SKU-D", "Produto Delta",   300.0,  15.0,  45.0, 120.0,  5.0,  76.77,  48.23, 0.1608),
    ]
    conn = _sq.connect(str(tmp_db))
    conn.executemany("""
        INSERT INTO fato_vendas
        (data_referencia, fonte, sku, produto, receita_total, frete, comissao_ml,
         custo_produto, incentivo, imposto, total_liquido, margem)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    conn.close()
    return tmp_db


# ── DataFrame helpers ─────────────────────────────────────────────────────────

@pytest.fixture
def df_vendas_simples():
    """5 SKUs com receitas e margens variadas para testar classificação."""
    return pd.DataFrame({
        "sku":          ["S1", "S2", "S3", "S4", "S5"],
        "produto":      ["P1", "P2", "P3", "P4", "P5"],
        "receita_total":[1000.0, 800.0, 400.0, 300.0, 200.0],
        "total_liquido":[ 250.0, 120.0, 100.0,  30.0, -20.0],
        "margem":       [  0.25,  0.15,  0.25,  0.10, -0.10],
        "custo_produto":[ 300.0, 400.0, 150.0, 150.0, 150.0],
        "frete":        [  50.0,  40.0,  20.0,  15.0,  10.0],
        "comissao_ml":  [ 150.0, 120.0,  60.0,  45.0,  30.0],
        "imposto":      [ 255.9, 204.7, 102.4,  76.8,  51.2],
        "incentivo":    [   5.9,   4.7,   2.4,   0.8,   1.2],
    })
