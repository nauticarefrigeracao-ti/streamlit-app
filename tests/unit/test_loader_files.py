"""Testes unitários — src/etl/loader.py (load_file / _read_csv)"""

import csv
from pathlib import Path

import pandas as pd
import pytest

from src.etl.loader import load_file


class TestLoadFile:

    def test_carrega_xlsx(self, tmp_path):
        df_orig = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        path = tmp_path / "test.xlsx"
        df_orig.to_excel(path, index=False)
        df = load_file(path)
        assert list(df.columns) == ["A", "B"]
        assert len(df) == 2

    def test_carrega_csv_utf8(self, tmp_path):
        path = tmp_path / "test.csv"
        path.write_text("SKU,Produto,Total\nSK-1,Alpha,1000\nSK-2,Beta,500\n", encoding="utf-8")
        df = load_file(path)
        assert "SKU" in df.columns
        assert len(df) == 2

    def test_carrega_csv_latin1(self, tmp_path):
        path = tmp_path / "test.csv"
        path.write_bytes("SKU,Produto,Total\nSK-1,Ação,1000\n".encode("latin-1"))
        df = load_file(path)
        assert len(df) == 1

    def test_carrega_csv_com_ponto_virgula(self, tmp_path):
        path = tmp_path / "test.csv"
        path.write_text("SKU;Produto;Total\nSK-1;Alpha;1000\n", encoding="utf-8")
        df = load_file(path)
        assert len(df.columns) > 1

    def test_retorna_dataframe(self, tmp_path):
        path = tmp_path / "test.csv"
        path.write_text("A,B\n1,2\n", encoding="utf-8")
        result = load_file(path)
        assert isinstance(result, pd.DataFrame)

    def test_formato_nao_suportado_levanta_erro(self, tmp_path):
        path = tmp_path / "test.txt"
        path.write_text("dados")
        with pytest.raises(ValueError, match="não suportado"):
            load_file(path)

    def test_todas_colunas_como_string(self, tmp_path):
        path = tmp_path / "test.csv"
        path.write_text("Qtd,Valor\n10,1000.50\n", encoding="utf-8")
        df = load_file(path)
        # pandas >= 2 pode retornar StringDtype ou object — ambos são tipos de string
        assert df["Qtd"].iloc[0] == "10"  # valor é string, não int

    def test_xlsx_preserva_nomes_originais(self, tmp_path):
        df_orig = pd.DataFrame({
            "PRODUTOS FULL": ["Alpha"],
            "SKU": ["SK-1"],
            "Total": ["1.000,00"],
        })
        path = tmp_path / "dados.xlsx"
        df_orig.to_excel(path, index=False)
        df = load_file(path)
        assert "PRODUTOS FULL" in df.columns
        assert "SKU" in df.columns
