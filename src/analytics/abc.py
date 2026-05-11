"""
Curva ABC — mesmo algoritmo, coluna configurável.
Classe A: top 80% acumulado
Classe B: 80-95%
Classe C: restante
"""

import pandas as pd


def calcular_abc(df: pd.DataFrame, coluna: str = "receita_total") -> pd.DataFrame:
    """
    Recebe DataFrame com a coluna de métricas e devolve com colunas adicionais:
    'perc_acumulado' e 'abc' (A / B / C).

    Args:
        df: deve conter ao menos 'sku', 'produto' e `coluna`
        coluna: 'receita_total', 'total_liquido' ou 'quantidade' (quando disponível)
    """
    df = df[df[coluna] > 0].copy()
    df = df.sort_values(coluna, ascending=False).reset_index(drop=True)

    total = df[coluna].sum()
    if total == 0:
        df["perc_acumulado"] = 0.0
        df["abc"] = "C"
        return df

    df["perc_acumulado"] = df[coluna].cumsum() / total

    # Classify by cumsum *before* this product is added (shift by 1).
    # This ensures the product that crosses the 80% threshold is still class A,
    # not B — and a single-product portfolio is always A, never C.
    prev = df["perc_acumulado"].shift(1).fillna(0.0)
    df["abc"] = prev.apply(lambda p: "A" if p < 0.80 else ("B" if p < 0.95 else "C"))
    return df


def resumo_abc(df: pd.DataFrame) -> pd.DataFrame:
    """Contagem e participação por classe ABC."""
    total_receita = df["receita_total"].sum()
    resumo = (
        df.groupby("abc")
        .agg(qtd_skus=("sku", "count"), receita=("receita_total", "sum"))
        .reset_index()
    )
    resumo["pct_receita"] = resumo["receita"] / total_receita
    return resumo.sort_values("abc")
