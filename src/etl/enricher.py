"""
Enriquecimento: calcula imposto, total_liquido e margem.
Recebe DataFrame limpo, devolve DataFrame com colunas derivadas.
"""

import pandas as pd

from src.config import TAXA_IMPOSTO


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["imposto"] = df["receita_total"] * TAXA_IMPOSTO
    df["total_liquido"] = (
        df["receita_total"]
        - df["frete"]
        - df["comissao_ml"]
        - df["imposto"]
        - df["custo_produto"]
        + df["incentivo"]
    )
    df["margem"] = df.apply(
        lambda r: r["total_liquido"] / r["receita_total"] if r["receita_total"] != 0 else 0.0,
        axis=1,
    )
    return df
