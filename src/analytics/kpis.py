"""
KPIs consolidados do período.
Todas as queries via SQLite — Streamlit recebe DataFrames prontos.
"""

import pandas as pd

from src.db.connection import get_connection


def get_periodos() -> list[str]:
    """Lista todos os períodos disponíveis no banco, mais recente primeiro."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT data_referencia FROM fato_vendas ORDER BY data_referencia DESC"
        ).fetchall()
    return [r[0] for r in rows]


def get_kpis(periodo: str) -> dict:
    """KPIs consolidados para um período (YYYY-MM-DD)."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                SUM(receita_total)  AS fat_bruto,
                SUM(total_liquido)  AS fat_liquido,
                SUM(total_liquido) / NULLIF(SUM(receita_total), 0) AS margem_global,
                COUNT(*)            AS total_skus,
                SUM(CASE WHEN margem < 0 THEN 1 ELSE 0 END) AS skus_prejuizo
            FROM fato_vendas
            WHERE data_referencia = ?
            """,
            (periodo,),
        ).fetchone()

    return {
        "fat_bruto":     row[0] or 0.0,
        "fat_liquido":   row[1] or 0.0,
        "margem_global": row[2] or 0.0,
        "total_skus":    row[3] or 0,
        "skus_prejuizo": row[4] or 0,
    }


def get_vendas(periodo: str) -> pd.DataFrame:
    """Todos os SKUs do período com métricas completas + margem histórica média."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                v.sku, v.produto,
                v.receita_total, v.frete, v.comissao_ml, v.custo_produto,
                v.incentivo, v.imposto, v.total_liquido, v.margem,
                h.margem_media
            FROM fato_vendas v
            LEFT JOIN (
                SELECT sku, AVG(margem) AS margem_media
                FROM fato_vendas
                GROUP BY sku
            ) h ON v.sku = h.sku
            WHERE v.data_referencia = ?
            ORDER BY v.receita_total DESC
            """,
            conn,
            params=(periodo,),
        )
    return df


def get_composicao_custos(periodo: str) -> dict:
    """Decomposição: onde vai cada R$1 de receita bruta."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                SUM(receita_total)  AS receita,
                SUM(imposto)        AS imposto,
                SUM(frete)          AS frete,
                SUM(comissao_ml)    AS comissao,
                SUM(custo_produto)  AS custo_produto,
                SUM(total_liquido)  AS liquido
            FROM fato_vendas
            WHERE data_referencia = ?
            """,
            (periodo,),
        ).fetchone()

    receita = row[0] or 1.0  # evita divisão por zero
    pct_imp = round((row[1] or 0) / receita * 100, 1)
    return {
        f"Imposto ({pct_imp:.1f}%)": (row[1] or 0) / receita,
        "Frete":                     (row[2] or 0) / receita,
        "Comissão ML":               (row[3] or 0) / receita,
        "Custo do Produto":          (row[4] or 0) / receita,
        "Margem Líquida":            (row[5] or 0) / receita,
    }


def get_comparativo(periodo_atual: str, periodo_anterior: str) -> pd.DataFrame:
    """Compara dois períodos por SKU (faturamento e margem)."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                a.sku,
                a.produto,
                a.receita_total  AS receita_atual,
                b.receita_total  AS receita_anterior,
                a.margem         AS margem_atual,
                b.margem         AS margem_anterior,
                (a.receita_total - b.receita_total)     AS delta_receita,
                (a.margem - b.margem)                   AS delta_margem
            FROM fato_vendas a
            LEFT JOIN fato_vendas b
                ON a.sku = b.sku AND b.data_referencia = ?
            WHERE a.data_referencia = ?
            ORDER BY delta_receita DESC
            """,
            conn,
            params=(periodo_anterior, periodo_atual),
        )
    return df


def get_serie_temporal() -> "pd.DataFrame":
    """KPIs mensais para gráficos de tendência temporal."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                data_referencia,
                SUM(receita_total)  AS fat_bruto,
                SUM(total_liquido)  AS fat_liquido,
                SUM(total_liquido) / NULLIF(SUM(receita_total), 0) AS margem_global,
                AVG(margem)         AS margem_media,
                COUNT(*)            AS total_skus
            FROM fato_vendas
            GROUP BY data_referencia
            ORDER BY data_referencia
            """,
            conn,
        )
    return df


def get_margem_por_periodo(top_n: int = 25) -> "pd.DataFrame":
    """Margem dos top N SKUs (por receita acumulada) × todos os períodos."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            WITH top_skus AS (
                SELECT sku
                FROM fato_vendas
                GROUP BY sku
                ORDER BY SUM(receita_total) DESC
                LIMIT ?
            )
            SELECT v.sku, v.produto, v.data_referencia, v.margem, v.receita_total
            FROM fato_vendas v
            INNER JOIN top_skus t ON v.sku = t.sku
            ORDER BY v.receita_total DESC, v.data_referencia
            """,
            conn,
            params=(top_n,),
        )
    return df
