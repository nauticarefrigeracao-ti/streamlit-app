import os
from pathlib import Path

# --- Paths ---
ROOT_DIR = Path(__file__).parent.parent
DB_PATH = ROOT_DIR / "data" / "margem.db"
DATA_DIR = ROOT_DIR / "data"

# --- Regras de negócio ---
TAXA_IMPOSTO = 0.2559  # 25,59% sobre receita_total

# --- Mapeamento de colunas do Excel/CSV ---
# Chave: nome canônico interno | Valor: nome(s) possível(is) no arquivo fonte
COLUMN_MAP = {
    "produto":        ["PRODUTOS FULL", "produto"],
    "sku":            ["SKU", "sku"],
    "receita_total":  ["Total", "total"],
    "frete":          ["Diferencial de frete", "diferencial de frete"],
    "comissao_ml":    ["Total comissão", "total comissão", "Total comissao"],
    "custo_produto":  ["Custo dos produtos", "custo dos produtos"],
    "incentivo":      ["Total incentivo", "total incentivo"],
}

# Colunas do Excel que são ignoradas (resumos do período, ads zerados, etc.)
COLUMNS_IGNORE = [
    "N° Pedido", "N Pedido",
    "Total comissão marketplace",
    "0,00%",
    "IMPOSTO",           # recalculamos — não confiamos no valor do Excel
    "Total líquido",     # derivado
    "MARGEM",            # derivado
    "MARGEM MÉDIA",      # resumo do período
    "FAT. BRUTO",        # resumo do período
    "FAT. LIQ",          # resumo do período
]

# --- GitHub Releases (backup/restore) ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "")
GITHUB_REPO  = os.environ.get("GITHUB_REPO", "")
DB_ASSET_NAME = "margem.db"

# --- Streamlit ---
APP_TITLE = "Análise de Margem e Faturamento"
