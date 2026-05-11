"""Testes unitários — src/etl/loader.py (infer_period)"""

import pytest
from src.etl.loader import infer_period


class TestInferPeriod:
    """Testa os padrões de nome de arquivo suportados pelo ETL."""

    # ── Padrões suportados ─────────────────────────────────────────────────────

    def test_mes_abreviado_ponto_ano(self):
        assert infer_period("MARGEM FEV.2026 FULL.csv") == "2026-02-01"

    def test_mes_abreviado_espaco_ano(self):
        assert infer_period("MARGEM JAN 2025.csv") == "2025-01-01"

    def test_mes_abreviado_underscore_ano(self):
        assert infer_period("margem_jan.2025.xlsx") == "2025-01-01"

    def test_mes_abreviado_case_insensitive(self):
        assert infer_period("VENDAS ABR.2024.xlsx") == "2024-04-01"

    def test_mes_abreviado_minusculo(self):
        assert infer_period("resultado_dez.2025.xlsx") == "2025-12-01"

    def test_mes_completo_com_acento(self):
        assert infer_period("MARGEM MARÇO 2025 FULL.csv") == "2025-03-01"

    def test_mes_completo_janeiro(self):
        assert infer_period("MARGEM JANEIRO 2024.csv") == "2024-01-01"

    def test_mes_completo_dezembro(self):
        assert infer_period("relatorio_dezembro.2024.csv") == "2024-12-01"

    def test_todos_meses_abreviados(self):
        meses = {
            "jan": "01", "fev": "02", "mar": "03", "abr": "04",
            "mai": "05", "jun": "06", "jul": "07", "ago": "08",
            "set": "09", "out": "10", "nov": "11", "dez": "12",
        }
        for abrev, num in meses.items():
            result = infer_period(f"MARGEM {abrev.upper()}.2025 FULL.csv")
            assert result == f"2025-{num}-01", f"falhou para {abrev}"

    def test_ano_correto_extraido(self):
        assert infer_period("VENDAS NOV.2023.xlsx").startswith("2023")
        assert infer_period("VENDAS NOV.2024.xlsx").startswith("2024")

    # ── Padrões não suportados — retornam None ────────────────────────────────

    def test_sem_data_retorna_none(self):
        assert infer_period("vendas.xlsx") is None

    def test_mes_numerico_retorna_none(self):
        # "mes3.xls" não é suportado — formato numérico não reconhecido
        assert infer_period("mes3.xls") is None

    def test_iso_date_retorna_none(self):
        assert infer_period("2025-03.xlsx") is None

    def test_string_vazia_retorna_none(self):
        assert infer_period("") is None

    def test_marco_sem_acento_retorna_none(self):
        # "MARCO" sem acento não bate no full_months nem no regex de abreviação
        assert infer_period("MARGEM MARCO 2025.csv") is None
