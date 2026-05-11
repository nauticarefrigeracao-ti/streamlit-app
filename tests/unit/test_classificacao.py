"""Testes unitários — src/analytics/classificacao.py"""

import math

import pandas as pd
import pytest

from src.analytics.classificacao import classificar, resumo_classificacao


def _df_padrao():
    """DataFrame com os 5 status representados."""
    return pd.DataFrame({
        "sku":          ["SE", "SV", "SO", "SP", "PR"],
        "produto":      ["Estrela", "VolCego", "Opor", "Parado", "Problema"],
        # mediana de receita = 300 (valores: 100,200,300,400,500 → med=300)
        # mediana de margem (positivos) = 0.20 (valores: 0.10,0.20,0.20,0.30 → med=0.20)
        "receita_total": [500.0, 400.0, 100.0, 200.0, 300.0],
        "margem":        [0.30,  0.10,  0.30,  0.10, -0.10],
        "total_liquido": [150.0, 40.0,  30.0,  20.0, -30.0],
        "custo_produto": [100.0]*5,
        "frete":         [10.0]*5,
        "comissao_ml":   [50.0]*5,
        "imposto":       [30.0]*5,
        "incentivo":     [0.0]*5,
    })


class TestClassificar:

    def test_status_estrela(self):
        df = classificar(_df_padrao())
        assert df[df["sku"] == "SE"]["status"].iloc[0] == "Estrela"

    def test_status_volume_cego(self):
        df = classificar(_df_padrao())
        assert df[df["sku"] == "SV"]["status"].iloc[0] == "Volume Cego"

    def test_status_oportunidade(self):
        df = classificar(_df_padrao())
        assert df[df["sku"] == "SO"]["status"].iloc[0] == "Oportunidade"

    def test_status_parado(self):
        df = classificar(_df_padrao())
        assert df[df["sku"] == "SP"]["status"].iloc[0] == "Parado"

    def test_status_problema_margem_negativa(self):
        df = classificar(_df_padrao())
        assert df[df["sku"] == "PR"]["status"].iloc[0] == "Problema"

    def test_margem_zero_nao_e_problema(self):
        df = pd.DataFrame({
            "sku": ["A"], "produto": ["P"],
            "receita_total": [100.0], "margem": [0.0],
            "total_liquido": [0.0], "custo_produto": [50.0],
            "frete": [5.0], "comissao_ml": [10.0],
            "imposto": [10.0], "incentivo": [0.0],
        })
        result = classificar(df)
        assert result.iloc[0]["status"] != "Problema"

    def test_todos_com_margem_negativa_sao_problema(self):
        df = pd.DataFrame({
            "sku": ["A", "B", "C"], "produto": ["P1", "P2", "P3"],
            "receita_total": [100.0, 200.0, 300.0],
            "margem":        [-0.10, -0.05, -0.20],
            "total_liquido": [-10.0, -10.0, -60.0],
            "custo_produto": [50.0]*3, "frete": [5.0]*3,
            "comissao_ml":   [10.0]*3, "imposto": [10.0]*3,
            "incentivo":     [0.0]*3,
        })
        result = classificar(df)
        assert (result["status"] == "Problema").all()

    def test_nao_modifica_df_original(self):
        df = _df_padrao()
        cols_antes = set(df.columns)
        classificar(df)
        assert "status" not in df.columns
        assert set(df.columns) == cols_antes

    def test_coluna_status_adicionada(self):
        df = classificar(_df_padrao())
        assert "status" in df.columns

    def test_thresholds_baseados_em_medianas(self):
        # Produto exatamente na mediana de receita e margem deve ser Estrela
        # (receita >= med e margem >= med)
        df = pd.DataFrame({
            "sku": ["X"], "produto": ["Y"],
            "receita_total": [300.0],  # igual à mediana
            "margem":        [0.20],   # igual à mediana positiva
            "total_liquido": [60.0],
            "custo_produto": [100.0], "frete": [10.0],
            "comissao_ml":   [50.0],  "imposto": [30.0],
            "incentivo":     [0.0],
        })
        merged = pd.concat([_df_padrao(), df], ignore_index=True)
        result = classificar(merged)
        status_x = result[result["sku"] == "X"]["status"].iloc[0]
        assert status_x == "Estrela"

    def test_df_com_produto_unico(self):
        df = pd.DataFrame({
            "sku": ["SOLO"], "produto": ["Único"],
            "receita_total": [1000.0], "margem": [0.25],
            "total_liquido": [250.0], "custo_produto": [300.0],
            "frete": [50.0], "comissao_ml": [150.0],
            "imposto": [255.9], "incentivo": [5.9],
        })
        result = classificar(df)
        assert len(result) == 1
        assert result.iloc[0]["status"] in {"Estrela", "Volume Cego", "Oportunidade", "Parado"}


class TestResumoClassificacao:

    def test_tem_colunas_obrigatorias(self):
        df = classificar(_df_padrao())
        res = resumo_classificacao(df)
        assert all(c in res.columns for c in ["status", "qtd", "receita", "margem_media"])

    def test_qtd_soma_total(self):
        df = classificar(_df_padrao())
        res = resumo_classificacao(df)
        assert res["qtd"].sum() == len(df)

    def test_receita_total_correta(self):
        df = classificar(_df_padrao())
        res = resumo_classificacao(df)
        assert math.isclose(res["receita"].sum(), df["receita_total"].sum(), abs_tol=0.01)

    def test_ordenado_por_receita_decrescente(self):
        df = classificar(_df_padrao())
        res = resumo_classificacao(df)
        receitas = res["receita"].tolist()
        assert receitas == sorted(receitas, reverse=True)

    def test_margem_media_por_status(self):
        df = classificar(_df_padrao())
        res = resumo_classificacao(df)
        # Status Problema tem margem negativa
        prob_row = res[res["status"] == "Problema"]
        if not prob_row.empty:
            assert prob_row["margem_media"].iloc[0] < 0
