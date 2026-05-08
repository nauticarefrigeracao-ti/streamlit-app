"""
Limpeza e normalização do DataFrame bruto.
- Mapeia colunas do Excel para nomes canônicos
- Converte valores BRL ("R$ 1.234,56") para float
- Remove linhas sem SKU (linhas de resumo/rodapé do Excel)
"""

import re
import math

import pandas as pd

from src.config import COLUMN_MAP


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = _rename_columns(df)
    df = _drop_empty_rows(df)
    df = _cast_floats(df)
    df["sku"] = df["sku"].str.strip().str.upper()
    df["produto"] = df["produto"].str.strip()
    return df.reset_index(drop=True)


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for canonical, candidates in COLUMN_MAP.items():
        for col in df.columns:
            if col.strip() in candidates:
                rename[col] = canonical
                break
    missing = [c for c in COLUMN_MAP if c not in rename.values()]
    if missing:
        raise ValueError(f"Colunas não encontradas no arquivo: {missing}")
    return df.rename(columns=rename)[list(COLUMN_MAP.keys())]


def _drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["sku"].notna() & (df["sku"].str.strip() != "")].copy()


def _cast_floats(df: pd.DataFrame) -> pd.DataFrame:
    float_cols = ["receita_total", "frete", "comissao_ml", "custo_produto", "incentivo"]
    for col in float_cols:
        df[col] = df[col].apply(limpar_valor)
    return df


def limpar_valor(valor) -> float:
    """Converte string BRL ("R$ 1.234,56") ou numérico para float.
    Testado em produção no sistema de devoluções.
    """
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        try:
            if math.isnan(float(valor)):
                return 0.0
        except Exception:
            pass
        return float(valor)

    s = str(valor).strip()
    s = s.replace("R$", "").replace("$", "").replace(" ", "").replace(" ", "")

    # parênteses → negativo: "(1.234,56)" → "-1234.56"
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]

    if not s or s.lower() == "nan":
        return 0.0

    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        # último separador é decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")   # BR: "1.234,56"
        else:
            s = s.replace(",", "")                      # US: "1,234.56"
    elif has_comma:
        s = s.replace(",", ".")
    # has_dot only → já está no formato float

    try:
        return float(s)
    except ValueError:
        return 0.0
