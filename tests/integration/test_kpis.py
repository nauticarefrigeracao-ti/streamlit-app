"""Testes de integração — src/analytics/kpis.py"""

import math

import pandas as pd
import pytest


class TestGetPeriodos:

    def test_retorna_lista(self, seeded_db):
        from src.analytics.kpis import get_periodos
        periodos = get_periodos()
        assert isinstance(periodos, list)

    def test_mais_recente_primeiro(self, seeded_db):
        from src.analytics.kpis import get_periodos
        periodos = get_periodos()
        assert periodos[0] > periodos[-1]

    def test_dois_periodos_inseridos(self, seeded_db):
        from src.analytics.kpis import get_periodos
        assert len(get_periodos()) == 2

    def test_sem_dados_retorna_lista_vazia(self, tmp_db):
        from src.analytics.kpis import get_periodos
        assert get_periodos() == []


class TestGetKpis:

    def test_retorna_dict_com_chaves_esperadas(self, seeded_db):
        from src.analytics.kpis import get_kpis
        kpis = get_kpis("2025-01-01")
        for k in ["fat_bruto", "fat_liquido", "margem_global", "total_skus", "skus_prejuizo"]:
            assert k in kpis

    def test_fat_bruto_correto(self, seeded_db):
        from src.analytics.kpis import get_kpis
        kpis = get_kpis("2025-01-01")
        # SKU-A=1000 + SKU-B=500 + SKU-C=200 = 1700
        assert math.isclose(kpis["fat_bruto"], 1700.0, abs_tol=0.01)

    def test_total_skus_correto(self, seeded_db):
        from src.analytics.kpis import get_kpis
        kpis = get_kpis("2025-01-01")
        assert kpis["total_skus"] == 3

    def test_skus_prejuizo_conta_margem_negativa(self, seeded_db):
        from src.analytics.kpis import get_kpis
        kpis = get_kpis("2025-01-01")
        assert kpis["skus_prejuizo"] == 1  # SKU-C tem margem negativa

    def test_periodo_inexistente_retorna_zeros(self, seeded_db):
        from src.analytics.kpis import get_kpis
        kpis = get_kpis("2099-01-01")
        assert kpis["fat_bruto"] == 0.0
        assert kpis["total_skus"] == 0

    def test_margem_global_entre_menos1_e_1(self, seeded_db):
        from src.analytics.kpis import get_kpis
        kpis = get_kpis("2025-01-01")
        assert -1.0 <= kpis["margem_global"] <= 1.0


class TestGetVendas:

    def test_retorna_dataframe(self, seeded_db):
        from src.analytics.kpis import get_vendas
        df = get_vendas("2025-01-01")
        assert isinstance(df, pd.DataFrame)

    def test_numero_correto_de_skus(self, seeded_db):
        from src.analytics.kpis import get_vendas
        df = get_vendas("2025-01-01")
        assert len(df) == 3

    def test_sem_skus_duplicados(self, seeded_db):
        from src.analytics.kpis import get_vendas
        df = get_vendas("2025-01-01")
        assert df["sku"].is_unique

    def test_colunas_obrigatorias(self, seeded_db):
        from src.analytics.kpis import get_vendas
        df = get_vendas("2025-01-01")
        for col in ["sku", "produto", "receita_total", "total_liquido", "margem", "margem_media"]:
            assert col in df.columns

    def test_ordenado_por_receita_decrescente(self, seeded_db):
        from src.analytics.kpis import get_vendas
        df = get_vendas("2025-01-01")
        receitas = df["receita_total"].tolist()
        assert receitas == sorted(receitas, reverse=True)

    def test_margem_media_preenchida(self, seeded_db):
        from src.analytics.kpis import get_vendas
        df = get_vendas("2025-01-01")
        assert df["margem_media"].notna().all()

    def test_periodo_inexistente_retorna_vazio(self, seeded_db):
        from src.analytics.kpis import get_vendas
        df = get_vendas("2099-01-01")
        assert len(df) == 0


class TestGetComparativo:

    def test_retorna_dataframe(self, seeded_db):
        from src.analytics.kpis import get_comparativo
        df = get_comparativo("2025-02-01", "2025-01-01")
        assert isinstance(df, pd.DataFrame)

    def test_colunas_obrigatorias(self, seeded_db):
        from src.analytics.kpis import get_comparativo
        df = get_comparativo("2025-02-01", "2025-01-01")
        for col in ["sku", "receita_atual", "receita_anterior", "margem_atual", "margem_anterior", "delta_receita"]:
            assert col in df.columns

    def test_sem_skus_duplicados(self, seeded_db):
        from src.analytics.kpis import get_comparativo
        df = get_comparativo("2025-02-01", "2025-01-01")
        assert df["sku"].is_unique

    def test_sku_novo_aparece_sem_anterior(self, seeded_db):
        # SKU-D existe em fev mas não em jan — receita_anterior deve ser NULL/NaN
        from src.analytics.kpis import get_comparativo
        df = get_comparativo("2025-02-01", "2025-01-01")
        sku_d = df[df["sku"] == "SKU-D"]
        assert not sku_d.empty
        assert pd.isna(sku_d["receita_anterior"].iloc[0])

    def test_sku_existente_tem_ambos_periodos(self, seeded_db):
        from src.analytics.kpis import get_comparativo
        df = get_comparativo("2025-02-01", "2025-01-01")
        sku_a = df[df["sku"] == "SKU-A"]
        assert not sku_a.empty
        assert not pd.isna(sku_a["receita_atual"].iloc[0])
        assert not pd.isna(sku_a["receita_anterior"].iloc[0])

    def test_delta_receita_calculado(self, seeded_db):
        from src.analytics.kpis import get_comparativo
        df = get_comparativo("2025-02-01", "2025-01-01")
        sku_a = df[df["sku"] == "SKU-A"].iloc[0]
        # jan=1000, fev=1200 → delta=200
        assert math.isclose(sku_a["delta_receita"], 200.0, abs_tol=0.01)


class TestGetComposicaoCustos:

    def test_retorna_dict(self, seeded_db):
        from src.analytics.kpis import get_composicao_custos
        comp = get_composicao_custos("2025-01-01")
        assert isinstance(comp, dict)

    def test_tem_componentes_esperados(self, seeded_db):
        from src.analytics.kpis import get_composicao_custos
        comp = get_composicao_custos("2025-01-01")
        keys_str = " ".join(comp.keys())
        assert "Imposto" in keys_str
        assert "Frete" in keys_str
        assert "Margem" in keys_str

    def test_valores_entre_zero_e_um(self, seeded_db):
        from src.analytics.kpis import get_composicao_custos
        comp = get_composicao_custos("2025-01-01")
        for k, v in comp.items():
            assert -1.0 <= v <= 1.5, f"{k}={v} fora do intervalo esperado"

    def test_componentes_somam_aproximadamente_um(self, seeded_db):
        from src.analytics.kpis import get_composicao_custos
        comp = get_composicao_custos("2025-01-01")
        total = sum(comp.values())
        assert math.isclose(total, 1.0, abs_tol=0.02)

    def test_periodo_inexistente_nao_levanta_erro(self, seeded_db):
        from src.analytics.kpis import get_composicao_custos
        comp = get_composicao_custos("2099-01-01")
        assert isinstance(comp, dict)


class TestGetSerieTemporal:

    def test_retorna_dataframe(self, seeded_db):
        from src.analytics.kpis import get_serie_temporal
        df = get_serie_temporal()
        assert isinstance(df, pd.DataFrame)

    def test_dois_periodos_retornados(self, seeded_db):
        from src.analytics.kpis import get_serie_temporal
        df = get_serie_temporal()
        assert len(df) == 2

    def test_colunas_obrigatorias(self, seeded_db):
        from src.analytics.kpis import get_serie_temporal
        df = get_serie_temporal()
        for col in ["data_referencia", "fat_bruto", "fat_liquido", "margem_global"]:
            assert col in df.columns

    def test_ordenado_por_data(self, seeded_db):
        from src.analytics.kpis import get_serie_temporal
        df = get_serie_temporal()
        datas = df["data_referencia"].tolist()
        assert datas == sorted(datas)

    def test_fat_bruto_positivo(self, seeded_db):
        from src.analytics.kpis import get_serie_temporal
        df = get_serie_temporal()
        assert (df["fat_bruto"] > 0).all()


class TestGetTimelineProdutos:

    def test_retorna_dataframe(self, seeded_db):
        from src.analytics.kpis import get_timeline_produtos
        df = get_timeline_produtos()
        assert isinstance(df, pd.DataFrame)

    def test_tem_todos_os_registros(self, seeded_db):
        from src.analytics.kpis import get_timeline_produtos
        df = get_timeline_produtos()
        assert len(df) == 6  # 3 skus × jan + 3 skus × fev (com SKU-D novo)

    def test_colunas_obrigatorias(self, seeded_db):
        from src.analytics.kpis import get_timeline_produtos
        df = get_timeline_produtos()
        for col in ["sku", "produto", "data_referencia", "receita_total", "total_liquido", "margem"]:
            assert col in df.columns


class TestGetMargemPorPeriodo:

    def test_retorna_dataframe(self, seeded_db):
        from src.analytics.kpis import get_margem_por_periodo
        df = get_margem_por_periodo(top_n=10)
        assert isinstance(df, pd.DataFrame)

    def test_respeita_top_n(self, seeded_db):
        from src.analytics.kpis import get_margem_por_periodo
        df = get_margem_por_periodo(top_n=2)
        skus_retornados = df["sku"].nunique()
        assert skus_retornados <= 2

    def test_colunas_obrigatorias(self, seeded_db):
        from src.analytics.kpis import get_margem_por_periodo
        df = get_margem_por_periodo()
        for col in ["sku", "produto", "data_referencia", "margem", "receita_total"]:
            assert col in df.columns
