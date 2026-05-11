"""Testes unitários — src/etl/enricher.py"""

import math

import pandas as pd
import pytest

from src.etl.enricher import enrich
from src.config import TAXA_IMPOSTO


def _row(**kw):
    defaults = dict(
        receita_total=1000.0, frete=50.0, comissao_ml=150.0,
        custo_produto=300.0, incentivo=20.0,
    )
    defaults.update(kw)
    return pd.DataFrame([defaults])


class TestEnrich:

    def test_imposto_calculado(self):
        df = enrich(_row(receita_total=1000.0))
        assert math.isclose(df["imposto"].iloc[0], 1000.0 * TAXA_IMPOSTO, abs_tol=0.01)

    def test_taxa_imposto_e_25_59(self):
        assert math.isclose(TAXA_IMPOSTO, 0.2559)

    def test_total_liquido_formula_completa(self):
        r, fr, cm, cp, inc = 1000.0, 50.0, 150.0, 300.0, 20.0
        imp = r * TAXA_IMPOSTO
        esperado = r - fr - cm - imp - cp + inc
        df = enrich(_row(receita_total=r, frete=fr, comissao_ml=cm,
                         custo_produto=cp, incentivo=inc))
        assert math.isclose(df["total_liquido"].iloc[0], esperado, abs_tol=0.01)

    def test_margem_e_total_liquido_sobre_receita(self):
        df = enrich(_row(receita_total=1000.0))
        liq = df["total_liquido"].iloc[0]
        margem_esperada = liq / 1000.0
        assert math.isclose(df["margem"].iloc[0], margem_esperada, abs_tol=1e-9)

    def test_receita_zero_margem_e_zero(self):
        df = enrich(_row(receita_total=0.0))
        assert df["margem"].iloc[0] == 0.0

    def test_margem_negativa_quando_custo_alto(self):
        df = enrich(_row(receita_total=100.0, frete=50.0, comissao_ml=50.0,
                         custo_produto=200.0, incentivo=0.0))
        assert df["total_liquido"].iloc[0] < 0
        assert df["margem"].iloc[0] < 0

    def test_incentivo_aumenta_total_liquido(self):
        sem_inc = enrich(_row(incentivo=0.0))["total_liquido"].iloc[0]
        com_inc = enrich(_row(incentivo=100.0))["total_liquido"].iloc[0]
        assert math.isclose(com_inc - sem_inc, 100.0, abs_tol=0.01)

    def test_frete_reduz_total_liquido(self):
        sem_frete = enrich(_row(frete=0.0))["total_liquido"].iloc[0]
        com_frete = enrich(_row(frete=100.0))["total_liquido"].iloc[0]
        assert math.isclose(sem_frete - com_frete, 100.0, abs_tol=0.01)

    def test_nao_modifica_df_original(self):
        original = _row()
        original_receita = original["receita_total"].iloc[0]
        enrich(original)
        assert original["receita_total"].iloc[0] == original_receita
        assert "imposto" not in original.columns

    def test_multiplas_linhas(self):
        df = pd.DataFrame({
            "receita_total": [1000.0, 500.0, 200.0],
            "frete":         [50.0, 25.0, 10.0],
            "comissao_ml":   [150.0, 75.0, 30.0],
            "custo_produto": [300.0, 150.0, 60.0],
            "incentivo":     [20.0, 10.0, 0.0],
        })
        result = enrich(df)
        assert len(result) == 3
        assert "imposto" in result.columns
        assert "total_liquido" in result.columns
        assert "margem" in result.columns
        # todos os impostos corretos
        for i, r in enumerate(df["receita_total"]):
            assert math.isclose(result["imposto"].iloc[i], r * TAXA_IMPOSTO, abs_tol=0.01)
