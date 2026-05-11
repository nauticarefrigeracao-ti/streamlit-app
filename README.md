# Análise de Margem e Faturamento — Grupo Náutica Refrigeração

A business intelligence dashboard that replaced a manual daily Excel routine with an automated, interactive margin and revenue analysis system — built solo from discovery to production.

---

## The Problem

The operations manager at Grupo Náutica Refrigeração spent significant time every day manually updating a spreadsheet to track product margin and revenue performance across their Mercado Livre catalog. The spreadsheet had broken cell references on 29 of 79 products (some excluded freight reimbursements from the formula, others excluded incentives). Decisions on pricing, stock priority, and product discontinuation were being made on unreliable data.

The goal: automate the entire process, fix the formula errors, and deliver actionable insights through a self-serve dashboard that non-technical stakeholders can actually use.

---

## What It Does

The system ingests monthly sales reports exported from Mercado Livre / Tiny ERP / Olist (CSV or Excel), runs them through a validated ETL pipeline, and presents the results across four analytical views:

**Visão Geral (Overview)**
KPIs for the selected period: gross revenue, net revenue, global margin, SKU count, and products in loss. Cost breakdown showing where each R$1 of gross revenue goes — tax, freight, commission, product cost, and net margin. Margin distribution histogram and full product table with export.

**Curva ABC (ABC Analysis)**
Pareto-based product classification across three perspectives: gross revenue, net profit, and product cost. Treemap for portfolio visualization. Identifies which products concentrate 80% of the business (Class A) versus the long tail consuming working capital without proportional return.

**Classificação (Product Classification)**
Each product is classified into one of five operational statuses using period medians as thresholds:
- **Estrela** — high revenue + high margin → protect stock
- **Volume Cego** — high revenue + low margin → reprice or renegotiate cost
- **Oportunidade** — low revenue + high margin → activate in campaigns
- **Parado** — low volume + low margin → evaluate discontinuation
- **Problema** — negative margin → immediate action required

Scatter matrix showing the full portfolio at a glance, summary cards per status, and detailed tables with per-status export.

**Comparativo (Period Comparison)**
Side-by-side delta analysis between any two loaded periods: revenue change (R$), margin change (p.p.), and a monthly evolution table showing each SKU's trajectory over time.

---

## Architecture

```
app/
├── main.py              # Streamlit entry point, sidebar, routing
└── views/
    ├── dashboard.py     # Visão Geral tab
    ├── abc.py           # Curva ABC tab
    ├── classificacao.py # Classificação tab
    └── comparativo.py   # Comparativo tab

src/
├── config.py            # Business constants (tax rate, column mapping)
├── db/
│   ├── connection.py    # SQLite connection factory (WAL mode)
│   ├── schema.py        # DDL + init
│   └── backup.py        # GitHub Releases backup/restore
├── etl/
│   ├── loader.py        # File reading (CSV/XLSX/XLS)
│   ├── cleaner.py       # Column mapping, BRL string parsing, row filtering
│   ├── enricher.py      # Derived columns: tax, total_liquido, margin
│   └── pipeline.py      # Orchestrator: file → DB
├── analytics/
│   ├── kpis.py          # All SQL queries → DataFrames
│   ├── abc.py           # Pareto ABC algorithm
│   └── classificacao.py # 5-status classification logic
└── utils/
    └── excel_export.py  # Styled Excel output with openpyxl

tests/
├── unit/                # 7 modules, pure function tests
└── integration/         # DB, pipeline, and KPI query tests
```

**Storage:** SQLite with WAL journal mode. Each row in `fato_vendas` represents one SKU for one period, with a `UNIQUE(data_referencia, sku, fonte)` constraint that makes re-imports idempotent. The database is backed up to GitHub Releases on every ingestion.

**Why SQLite:** The data volume is predictable and bounded (hundreds of SKUs, monthly cadence). SQLite eliminates operational overhead without sacrificing query expressiveness. WAL mode allows concurrent reads during writes, which matters in a Streamlit context where multiple users can be on the same session.

**ETL design:** Each stage is a pure function — `load_file → clean → enrich`. The cleaner handles the BRL number format ambiguity (`"1.234,56"` vs `"1,234.56"` vs `"-"` vs `None`) with a single well-tested `limpar_valor()` function. The enricher recalculates tax, net margin, and gross margin from scratch rather than trusting the source file's derived columns — this is intentional, since the original spreadsheet had formula errors.

**Formula:** `total_liquido = receita - frete - comissao - (receita × 25.59%) - custo + incentivo`

This was validated against the manager's Excel file. The system is more accurate: the Excel had broken references excluding freight and incentive from 29 products. For the 50 products where the Excel formula was correct, values match to floating-point precision.

---

## Business Logic Details

**Tax rate (25.59%):** Applied to gross revenue. Encompasses Simples Nacional tax brackets applicable to the operation. Stored as a named constant in `config.py` — not hardcoded in formulas.

**ABC classification:** Uses the shift-1 cumulative percentage approach. A product is Class A if its *previous* cumulative share was under 80%, not if its *current* cumulative share is under 80%. This distinction matters: a single dominant product (say, 90% of revenue) would be misclassified as B under the naive `<= 0.80` check. The correct Pareto algorithm classifies any product that pushes the running total past 80% as still being Class A.

**Product status thresholds:** Based on period medians, not fixed values. This makes the classification relative to the current portfolio composition — a healthy margin in a low-margin period would still be recognized as above-average.

---

## Tests

```
183 tests · 99% code coverage
```

```
src/analytics/abc.py           100%
src/analytics/classificacao.py 100%
src/analytics/kpis.py          100%
src/db/connection.py           100%
src/db/schema.py               100%
src/etl/cleaner.py             100%
src/etl/enricher.py            100%
src/etl/pipeline.py            100%
src/utils/excel_export.py      100%
src/etl/loader.py               95%   (.xls binary + CSV error path)
```

Unit tests cover all parsing edge cases: `None`, `NaN`, empty strings, BRL format, US format, negative values, parenthetical negatives. Integration tests run against an isolated SQLite instance in `tmp_path` — production data is never touched.

A real bug was caught during test development: `pipeline._upsert` was catching `Exception` broadly instead of `sqlite3.IntegrityError`, silently swallowing any database error (schema mismatch, disk full) and incrementing `rows_skipped` falsely.

Run the suite:
```bash
python -m pytest tests/ --cov=src --cov-config=.coveragerc
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit 1.50 |
| Data | pandas, SQLite (WAL) |
| Charts | Plotly Express |
| Excel export | openpyxl (styled: navy headers, color scales, freeze panes, auto-filter) |
| ETL | Pure Python — no Spark, no Airflow, no overhead |
| Tests | pytest + pytest-cov |
| Hosting | Streamlit Community Cloud |
| DB backup | GitHub Releases (binary asset per deploy) |

---

## Running Locally

Requires Python 3.10+.

```bash
git clone https://github.com/nauticarefrigeracao-ti/streamlit-app.git
cd streamlit-app
pip install -r requirements.txt
streamlit run app/main.py
```

Or double-click `Iniciar.bat` on Windows — it installs Python and all dependencies automatically on first run.

---

## What's Next

- Authentication layer (login/password per user)
- Multi-channel support (isolating Mercado Livre vs. Shopee vs. direct sales margins)
- Automated monthly ingestion via scheduled pipeline
- Forecasting module for margin trend projection

---

*Built by [Lucas Leite Gonzales](mailto:nauticarefrigeracao.ti@gmail.com) — solo development, from business discovery through ETL design, analytics logic, UI, testing, and deployment.*
