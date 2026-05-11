"""
Orquestra: arquivo → DB.
Único ponto de entrada para ingestão.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import DB_PATH
from src.db.connection import get_connection
from src.db.schema import init_db
from src.etl.loader import load_file, infer_period
from src.etl.cleaner import clean
from src.etl.enricher import enrich

logger = logging.getLogger(__name__)


def run(file_path: str | Path, data_referencia: str | None = None) -> dict:
    """
    Executa o pipeline completo para um arquivo.

    Args:
        file_path: caminho ou nome do arquivo (CSV / Excel)
        data_referencia: 'YYYY-MM-DD' do período; se None, infere do nome do arquivo

    Returns:
        dict com 'rows_inserted', 'rows_skipped', 'periodo', 'fonte'
    """
    p = Path(file_path)
    fonte = p.name

    periodo = data_referencia or infer_period(fonte)
    if not periodo:
        raise ValueError(
            f"Não foi possível inferir o período do arquivo '{fonte}'. "
            "Informe data_referencia no formato YYYY-MM-DD."
        )

    logger.info(f"Pipeline iniciado: {fonte} → período {periodo}")

    raw = load_file(p)
    df = clean(raw)
    df = enrich(df)

    df["data_referencia"] = periodo
    df["fonte"] = fonte
    df["data_ingestao"] = datetime.now().isoformat()

    init_db()
    inserted, skipped = _upsert(df)

    logger.info(f"Pipeline concluído: {inserted} inseridas, {skipped} ignoradas (duplicatas)")
    return {"rows_inserted": inserted, "rows_skipped": skipped, "periodo": periodo, "fonte": fonte}


def _upsert(df: pd.DataFrame) -> tuple[int, int]:
    cols = [
        "data_referencia", "fonte", "sku", "produto",
        "receita_total", "frete", "comissao_ml", "custo_produto", "incentivo",
        "imposto", "total_liquido", "margem", "data_ingestao",
    ]
    inserted = skipped = 0

    with get_connection() as conn:
        for _, row in df[cols].iterrows():
            try:
                conn.execute(
                    f"INSERT INTO fato_vendas ({', '.join(cols)}) VALUES ({', '.join(['?']*len(cols))})",
                    [row[c] for c in cols],
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()

    return inserted, skipped
