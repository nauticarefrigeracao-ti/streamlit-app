"""
Carrega CSV ou Excel de vendas → DataFrame bruto (sem transformações).
Responsabilidade única: ler o arquivo e retornar colunas originais.
"""

import re
from pathlib import Path

import pandas as pd


def load_file(path: str | Path) -> pd.DataFrame:
    """Lê CSV ou Excel e retorna DataFrame com colunas originais."""
    p = Path(path)
    if p.suffix.lower() == ".xlsx":
        df = pd.read_excel(p, dtype=str)
    elif p.suffix.lower() == ".xls":
        df = pd.read_excel(p, dtype=str, engine="calamine")
    elif p.suffix.lower() == ".csv":
        df = _read_csv(p)
    else:
        raise ValueError(f"Formato não suportado: {p.suffix}")
    return df


def _read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc)
            if len(df.columns) > 1:
                return df
            # provavelmente delimitador errado
            df = pd.read_csv(path, dtype=str, encoding=enc, sep=";")
            if len(df.columns) > 1:
                return df
        except Exception:
            continue
    raise ValueError(f"Não foi possível ler CSV: {path}")


def infer_period(filename: str) -> str:
    """
    Extrai data de referência (YYYY-MM-DD) do nome do arquivo.
    Exemplos:
      'MARGEM FEV.2026 FULL.csv'  → '2026-02-01'
      'MARGEM MARÇO 2025 FULL...' → '2025-03-01'
    Retorna None se não conseguir inferir.
    """
    months = {
        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
    }
    name = filename.lower()
    # padrão: "MES.ANO" ou "MES ANO"
    match = re.search(r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[.\s]+(\d{4})", name)
    if match:
        month = months[match.group(1)]
        year = int(match.group(2))
        return f"{year:04d}-{month:02d}-01"
    # padrão: "MARÇO 2025" (nome completo)
    full_months = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
        "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
        "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
    }
    for name_pt, num in full_months.items():
        m = re.search(rf"{name_pt}[.\s]+(\d{{4}})", name)
        if m:
            return f"{int(m.group(1)):04d}-{num:02d}-01"
    return None
