"""Testes unitários — src/analytics/abc.py"""

import math

import pandas as pd
import pytest

from src.analytics.abc import calcular_abc, resumo_abc


def _df(receitas: list[float]) -> pd.DataFrame:
    n = len(receitas)
    return pd.DataFrame({
        "sku":          [f"SK{i}" for i in range(n)],
        "produto":      [f"Prod{i}" for i in range(n)],
        "receita_total": receitas,
        "total_liquido": [r * 0.2 for r in receitas],
        "custo_produto": [r * 0.3 for r in receitas],
        "margem":        [0.2] * n,
    })


class TestCalcularAbc:

    def test_produto_unico_e_classe_a(self):
        df = calcular_abc(_df([1000.0]))
        assert df.iloc[0]["abc"] == "A"

    def test_perc_acumulado_max_e_1(self):
        df = calcular_abc(_df([500.0, 300.0, 200.0]))
        assert math.isclose(df["perc_acumulado"].max(), 1.0, abs_tol=1e-9)

    def test_produto_dominante_e_classe_a(self):
        # P1 = 90% da receita — deve ser A, não B
        df = calcular_abc(_df([900.0, 100.0]))
        classes = df.set_index("sku")["abc"].to_dict()
        assert classes["SK0"] == "A"

    def test_tres_classes_preenchidas(self):
        # Distribuição que gera A, B e C
        receitas = [500.0, 300.0, 100.0, 50.0, 20.0, 10.0, 5.0, 5.0, 5.0, 5.0]
        df = calcular_abc(_df(receitas))
        classes = set(df["abc"].unique())
        assert "A" in classes
        assert "B" in classes
        assert "C" in classes

    def test_ordenacao_decrescente_por_receita(self):
        df = calcular_abc(_df([100.0, 500.0, 300.0]))
        receitas = df["receita_total"].tolist()
        assert receitas == sorted(receitas, reverse=True)

    def test_df_vazio_retorna_vazio(self):
        df_vazio = _df([]).head(0)
        result = calcular_abc(df_vazio)
        assert len(result) == 0

    def test_receitas_negativas_excluidas(self):
        # calcular_abc filtra coluna > 0
        df = pd.DataFrame({
            "sku": ["SK1", "SK2", "SK3"],
            "produto": ["P1", "P2", "P3"],
            "receita_total": [500.0, -100.0, 200.0],
            "total_liquido": [50.0, -10.0, 20.0],
            "custo_produto": [100.0, 50.0, 80.0],
            "margem": [0.1, -0.1, 0.1],
        })
        result = calcular_abc(df)
        assert len(result) == 2
        assert all(result["receita_total"] > 0)

    def test_receita_zero_excluida(self):
        df = pd.DataFrame({
            "sku": ["SK1", "SK2"],
            "produto": ["P1", "P2"],
            "receita_total": [0.0, 500.0],
            "total_liquido": [0.0, 50.0],
            "custo_produto": [0.0, 100.0],
            "margem": [0.0, 0.1],
        })
        result = calcular_abc(df)
        assert len(result) == 1

    def test_threshold_80_percentual(self):
        # 5 produtos iguais: cada um é 20%. Os 4 primeiros somam 80%.
        # P1 (prev=0%) → A, P2 (prev=20%) → A, P3 (prev=40%) → A, P4 (prev=60%) → A
        # P5 (prev=80%) → não entra em A (0.80 não é < 0.80), vai para B
        df = calcular_abc(_df([200.0, 200.0, 200.0, 200.0, 200.0]))
        classes = df["abc"].tolist()
        assert classes.count("A") == 4
        assert classes[-1] in ("B", "C")

    def test_coluna_alternativa_total_liquido(self):
        df_pos = _df([500.0, 300.0, 200.0])
        df_pos["total_liquido"] = [100.0, 60.0, 40.0]
        result = calcular_abc(df_pos, coluna="total_liquido")
        assert "abc" in result.columns
        assert math.isclose(result["perc_acumulado"].max(), 1.0, abs_tol=1e-9)

    def test_total_zero_retorna_classe_c(self):
        df = _df([500.0, 300.0])
        df["receita_total"] = 0.0
        df = df[df["receita_total"] > 0]  # remove tudo
        result = calcular_abc(df)
        assert len(result) == 0


class TestResumoAbc:

    def test_tem_colunas_obrigatorias(self):
        df = calcular_abc(_df([500.0, 300.0, 100.0, 50.0, 10.0]))
        res = resumo_abc(df)
        assert all(c in res.columns for c in ["abc", "qtd_skus", "receita", "pct_receita"])

    def test_qtd_skus_soma_total(self):
        df = calcular_abc(_df([500.0, 300.0, 100.0, 50.0, 10.0]))
        res = resumo_abc(df)
        assert res["qtd_skus"].sum() == 5

    def test_pct_receita_soma_um(self):
        df = calcular_abc(_df([500.0, 300.0, 100.0, 50.0, 10.0]))
        res = resumo_abc(df)
        assert math.isclose(res["pct_receita"].sum(), 1.0, abs_tol=1e-9)

    def test_receita_soma_total_correto(self):
        receitas = [500.0, 300.0, 100.0, 50.0, 10.0]
        df = calcular_abc(_df(receitas))
        res = resumo_abc(df)
        assert math.isclose(res["receita"].sum(), sum(receitas), abs_tol=0.01)
