"""Testes de integração — src/etl/pipeline.py"""

import math
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_excel(tmp_path: Path, filename: str = "MARGEM JAN.2025 FULL.xlsx") -> Path:
    """Gera um Excel mínimo com colunas que o ETL consegue mapear."""
    df = pd.DataFrame({
        "PRODUTOS FULL":        ["Produto Alpha", "Produto Beta", "Produto Gamma"],
        "SKU":                  ["SKU-A", "SKU-B", "SKU-C"],
        "Total":                ["1.000,00", "500,50", "200,00"],
        "Diferencial de frete": ["50,00", "25,00", "10,00"],
        "Total comissão":       ["150,00", "75,00", "30,00"],
        "Custo dos produtos":   ["300,00", "150,00", "80,00"],
        "Total incentivo":      ["20,00", "10,00", "0,00"],
    })
    path = tmp_path / filename
    df.to_excel(path, index=False)
    return path


def _row_count(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    n = conn.execute("SELECT COUNT(*) FROM fato_vendas").fetchone()[0]
    conn.close()
    return n


# ── _upsert ───────────────────────────────────────────────────────────────────

class TestUpsert:

    def test_insere_linhas_novas(self, tmp_db):
        from src.etl.pipeline import _upsert
        df = pd.DataFrame({
            "data_referencia": ["2025-01-01"] * 3,
            "fonte":           ["arq.xls"] * 3,
            "sku":             ["A", "B", "C"],
            "produto":         ["P1", "P2", "P3"],
            "receita_total":   [100.0, 200.0, 300.0],
            "frete":           [5.0] * 3,
            "comissao_ml":     [15.0] * 3,
            "custo_produto":   [30.0] * 3,
            "incentivo":       [0.0] * 3,
            "imposto":         [25.59, 51.18, 76.77],
            "total_liquido":   [24.41, 58.82, 152.23],
            "margem":          [0.24, 0.29, 0.51],
            "data_ingestao":   ["2025-01-01T00:00:00"] * 3,
        })
        inserted, skipped = _upsert(df)
        assert inserted == 3
        assert skipped == 0
        assert _row_count(tmp_db) == 3

    def test_duplicata_contabilizada_em_skipped(self, tmp_db):
        from src.etl.pipeline import _upsert
        df = pd.DataFrame({
            "data_referencia": ["2025-01-01"],
            "fonte":           ["arq.xls"],
            "sku":             ["DUP"],
            "produto":         ["Dup Prod"],
            "receita_total":   [100.0],
            "frete":           [5.0],
            "comissao_ml":     [15.0],
            "custo_produto":   [30.0],
            "incentivo":       [0.0],
            "imposto":         [25.59],
            "total_liquido":   [24.41],
            "margem":          [0.24],
            "data_ingestao":   ["2025-01-01T00:00:00"],
        })
        _upsert(df)  # primeira vez
        inserted2, skipped2 = _upsert(df)  # duplicata
        assert inserted2 == 0
        assert skipped2 == 1
        assert _row_count(tmp_db) == 1  # só 1 linha no banco

    def test_mix_novos_e_duplicatas(self, tmp_db):
        from src.etl.pipeline import _upsert
        base = {
            "data_referencia": "2025-01-01", "fonte": "arq.xls",
            "produto": "P", "receita_total": 100.0, "frete": 5.0,
            "comissao_ml": 15.0, "custo_produto": 30.0, "incentivo": 0.0,
            "imposto": 25.59, "total_liquido": 24.41, "margem": 0.24,
            "data_ingestao": "now",
        }
        df1 = pd.DataFrame([{**base, "sku": "X"}, {**base, "sku": "Y"}])
        _upsert(df1)
        df2 = pd.DataFrame([{**base, "sku": "X"}, {**base, "sku": "Z"}])  # X=dup, Z=novo
        ins, skip = _upsert(df2)
        assert ins == 1
        assert skip == 1


# ── pipeline.run ──────────────────────────────────────────────────────────────

class TestPipelineRun:

    def test_run_insere_linhas(self, tmp_db, tmp_path):
        from src.etl.pipeline import run
        xls = _make_excel(tmp_path)
        result = run(xls)
        assert result["rows_inserted"] == 3
        assert result["rows_skipped"] == 0
        assert _row_count(tmp_db) == 3

    def test_run_retorna_periodo_inferido(self, tmp_db, tmp_path):
        from src.etl.pipeline import run
        xls = _make_excel(tmp_path, "MARGEM JAN.2025 FULL.xlsx")
        result = run(xls)
        assert result["periodo"] == "2025-01-01"

    def test_run_retorna_nome_fonte(self, tmp_db, tmp_path):
        from src.etl.pipeline import run
        xls = _make_excel(tmp_path, "MARGEM JAN.2025 FULL.xlsx")
        result = run(xls)
        assert result["fonte"] == "MARGEM JAN.2025 FULL.xlsx"

    def test_run_aceita_data_referencia_manual(self, tmp_db, tmp_path):
        from src.etl.pipeline import run
        xls = _make_excel(tmp_path, "dados_sem_data.xlsx")
        result = run(xls, data_referencia="2025-06-01")
        assert result["periodo"] == "2025-06-01"
        assert result["rows_inserted"] == 3

    def test_run_levanta_erro_sem_data_inferivel(self, tmp_db, tmp_path):
        from src.etl.pipeline import run
        xls = _make_excel(tmp_path, "dados_sem_data.xlsx")
        with pytest.raises(ValueError, match="período"):
            run(xls)

    def test_run_idempotente_segunda_carga(self, tmp_db, tmp_path):
        from src.etl.pipeline import run
        xls = _make_excel(tmp_path)
        run(xls)
        result2 = run(xls)
        assert result2["rows_inserted"] == 0
        assert result2["rows_skipped"] == 3
        assert _row_count(tmp_db) == 3  # não duplicou

    def test_run_dados_enriquecidos_no_banco(self, tmp_db, tmp_path):
        from src.etl.pipeline import run
        run(_make_excel(tmp_path))
        conn = sqlite3.connect(str(tmp_db))
        rows = conn.execute(
            "SELECT receita_total, imposto, total_liquido, margem FROM fato_vendas"
        ).fetchall()
        conn.close()
        for r, imp, liq, mg in rows:
            assert math.isclose(imp, r * 0.2559, abs_tol=0.02)
            if r > 0:
                assert math.isclose(mg, liq / r, abs_tol=1e-4)
