from src.db.connection import get_connection


_DDL = """
CREATE TABLE IF NOT EXISTS fato_vendas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    data_referencia TEXT    NOT NULL,  -- YYYY-MM-DD (primeiro dia do período)
    fonte          TEXT    NOT NULL,  -- nome original do arquivo carregado
    sku            TEXT    NOT NULL,
    produto        TEXT,
    receita_total  REAL    DEFAULT 0,
    frete          REAL    DEFAULT 0,
    comissao_ml    REAL    DEFAULT 0,
    custo_produto  REAL    DEFAULT 0,
    incentivo      REAL    DEFAULT 0,
    imposto        REAL    DEFAULT 0,  -- receita_total * TAXA_IMPOSTO
    total_liquido  REAL    DEFAULT 0,
    margem         REAL    DEFAULT 0,  -- total_liquido / receita_total
    data_ingestao  TEXT,
    UNIQUE(data_referencia, sku, fonte)
);

CREATE INDEX IF NOT EXISTS idx_fv_periodo ON fato_vendas(data_referencia);
CREATE INDEX IF NOT EXISTS idx_fv_sku     ON fato_vendas(sku);
"""


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(_DDL)
