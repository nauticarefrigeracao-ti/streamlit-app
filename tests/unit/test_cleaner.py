"""Testes unitários — src/etl/cleaner.py"""

import math

import pandas as pd
import pytest

from src.etl.cleaner import limpar_valor, clean, _drop_empty_rows, _cast_floats


# ── limpar_valor ──────────────────────────────────────────────────────────────

class TestLimparValor:

    def test_none_retorna_zero(self):
        assert limpar_valor(None) == 0.0

    def test_nan_retorna_zero(self):
        assert limpar_valor(float("nan")) == 0.0

    def test_string_vazia_retorna_zero(self):
        assert limpar_valor("") == 0.0

    def test_string_espacos_retorna_zero(self):
        assert limpar_valor("   ") == 0.0

    def test_traco_retorna_zero(self):
        assert limpar_valor("-") == 0.0

    def test_nan_string_retorna_zero(self):
        assert limpar_valor("nan") == 0.0

    def test_inteiro_zero(self):
        assert limpar_valor(0) == 0.0

    def test_inteiro_positivo(self):
        assert limpar_valor(42) == 42.0

    def test_float_passthrough(self):
        assert math.isclose(limpar_valor(3.14), 3.14)

    def test_brl_ponto_virgula(self):
        assert math.isclose(limpar_valor("1.234,56"), 1234.56)

    def test_brl_com_prefixo_rs(self):
        assert math.isclose(limpar_valor("R$ 1.234,56"), 1234.56)

    def test_brl_com_espaco_unicode(self):
        assert math.isclose(limpar_valor("R$ 1.234,56"), 1234.56)

    def test_formato_americano_virgula_ponto(self):
        assert math.isclose(limpar_valor("1,234.56"), 1234.56)

    def test_decimal_simples(self):
        assert math.isclose(limpar_valor("1234.56"), 1234.56)

    def test_negativo_brl(self):
        assert math.isclose(limpar_valor("-1.234,56"), -1234.56)

    def test_parenteses_negativo(self):
        assert math.isclose(limpar_valor("(1.234,56)"), -1234.56)

    def test_parenteses_com_rs(self):
        assert math.isclose(limpar_valor("(R$ 500,00)"), -500.0)

    def test_fracao_brl_menor_que_um(self):
        assert math.isclose(limpar_valor("0,5"), 0.5)

    def test_apenas_centavos_brl(self):
        assert math.isclose(limpar_valor("0,99"), 0.99)

    def test_valor_grande_brl(self):
        assert math.isclose(limpar_valor("1.000.000,00"), 1_000_000.0)

    def test_inteiro_brl(self):
        assert math.isclose(limpar_valor("500,00"), 500.0)

    def test_negativo_americano(self):
        assert math.isclose(limpar_valor("-1,234.56"), -1234.56)


# ── _drop_empty_rows ──────────────────────────────────────────────────────────

class TestDropEmptyRows:

    def _df(self, skus):
        return pd.DataFrame({"sku": skus, "produto": ["P"] * len(skus)})

    def test_remove_sku_nulo(self):
        df = self._df(["SKU-1", None, "SKU-2"])
        result = _drop_empty_rows(df)
        assert len(result) == 2
        assert result["sku"].tolist() == ["SKU-1", "SKU-2"]

    def test_remove_sku_string_vazia(self):
        df = self._df(["SKU-1", "", "SKU-2"])
        result = _drop_empty_rows(df)
        assert len(result) == 2

    def test_remove_sku_apenas_espacos(self):
        df = self._df(["SKU-1", "   ", "SKU-2"])
        result = _drop_empty_rows(df)
        assert len(result) == 2

    def test_preserva_todos_quando_ok(self):
        df = self._df(["SKU-A", "SKU-B", "SKU-C"])
        result = _drop_empty_rows(df)
        assert len(result) == 3

    def test_df_todo_vazio_retorna_vazio(self):
        df = self._df([None, "", "  "])
        result = _drop_empty_rows(df)
        assert len(result) == 0


# ── clean (integração parcial: rename + drop + cast) ──────────────────────────

class TestClean:

    def _raw_df(self, extra=None):
        """DataFrame com nomes de coluna que batem com COLUMN_MAP."""
        data = {
            "PRODUTOS FULL":       ["Produto A", "Produto B", None],
            "SKU":                 ["SK-001", "SK-002", ""],
            "Total":               ["R$ 1.000,00", "500,50", "200,00"],
            "Diferencial de frete":["50,00", "30,00", "20,00"],
            "Total comissão":      ["100,00", "75,00", "40,00"],
            "Custo dos produtos":  ["300,00", "200,00", "100,00"],
            "Total incentivo":     ["10,00", "0,00", "5,00"],
        }
        if extra:
            data.update(extra)
        return pd.DataFrame(data)

    def test_colunas_renomeadas_corretamente(self):
        df = clean(self._raw_df())
        assert "receita_total" in df.columns
        assert "frete" in df.columns
        assert "comissao_ml" in df.columns
        assert "custo_produto" in df.columns
        assert "incentivo" in df.columns
        assert "sku" in df.columns
        assert "produto" in df.columns

    def test_linhas_sem_sku_removidas(self):
        df = clean(self._raw_df())
        assert len(df) == 2  # terceira linha tem SKU vazio

    def test_sku_uppercased(self):
        raw = self._raw_df()
        raw["SKU"] = ["sk-001", "sk-002", ""]
        df = clean(raw)
        assert df["sku"].tolist() == ["SK-001", "SK-002"]

    def test_receita_convertida_para_float(self):
        df = clean(self._raw_df())
        assert df["receita_total"].dtype == float
        assert math.isclose(df["receita_total"].iloc[0], 1000.0)

    def test_coluna_faltando_levanta_valueerror(self):
        raw = pd.DataFrame({"SKU": ["X"], "Total": ["100"]})  # faltam colunas
        with pytest.raises(ValueError, match="Colunas não encontradas"):
            clean(raw)

    def test_reset_index(self):
        df = clean(self._raw_df())
        assert list(df.index) == [0, 1]
