# Análise de Margem e Faturamento — Grupo Náutica Refrigeração

**[🇧🇷 Português](#português) · [🇺🇸 English](#english)**

---

<a name="português"></a>
## 🇧🇷 Português

Um dashboard de inteligência de negócios que substituiu uma rotina manual diária em Excel por um sistema automatizado de análise de margem e faturamento — construído do zero por um desenvolvedor solo, da descoberta até a produção.

### O Problema

O gestor de operações do Grupo Náutica Refrigeração dedicava um tempo considerável todo dia atualizando manualmente uma planilha para acompanhar margem e faturamento por produto no catálogo do Mercado Livre. A planilha continha referências de célula quebradas em 29 dos 79 produtos — alguns excluindo o diferencial de frete da fórmula, outros excluindo os incentivos. Decisões de precificação, prioridade de estoque e descontinuação de produtos estavam sendo tomadas com dados incorretos.

O objetivo: automatizar o processo, corrigir os erros de fórmula e entregar insights acionáveis via dashboard que gestores não-técnicos consigam usar sem depender de TI.

### O Que Faz

O sistema ingere relatórios mensais exportados do Mercado Livre / Tiny ERP / Olist (CSV ou Excel), processa via pipeline ETL validado e apresenta os resultados em quatro visões analíticas:

**Visão Geral**
KPIs do período: faturamento bruto, faturamento líquido, margem global, total de SKUs e produtos em prejuízo. Decomposição de custos mostrando para onde vai cada R$1 de receita bruta — imposto, frete, comissão, custo de produto e margem líquida. Histograma de distribuição de margens e tabela completa com exportação.

**Curva ABC**
Classificação de produtos pelo princípio de Pareto em três perspectivas: faturamento bruto, lucro líquido e custo de produto. Treemap para visualização do portfólio. Identifica quais produtos concentram 80% do negócio (Classe A) versus a longa cauda consumindo capital de giro sem retorno proporcional.

**Classificação de Produtos**
Cada produto é classificado em um dos cinco status operacionais usando as medianas do período como thresholds:
- **Estrela** — alta receita + alta margem → proteger estoque
- **Volume Cego** — alta receita + baixa margem → revisar preço ou negociar custo
- **Oportunidade** — baixa receita + alta margem → ativar em campanha
- **Parado** — baixo volume + baixa margem → avaliar descontinuação
- **Problema** — margem negativa → ação imediata

Scatter matrix com todo o portfólio de relance, cards de resumo por status e tabelas detalhadas com exportação por status.

**Comparativo**
Análise de delta entre dois períodos: variação de receita (R$), variação de margem (p.p.) e tabela de evolução mensal mostrando a trajetória de cada SKU ao longo do tempo.

### Arquitetura

```
app/
├── main.py              # Entry point Streamlit, sidebar, roteamento
└── views/
    ├── dashboard.py     # Aba Visão Geral
    ├── abc.py           # Aba Curva ABC
    ├── classificacao.py # Aba Classificação
    └── comparativo.py   # Aba Comparativo

src/
├── config.py            # Constantes de negócio (taxa de imposto, mapeamento de colunas)
├── db/
│   ├── connection.py    # Fábrica de conexão SQLite (modo WAL)
│   ├── schema.py        # DDL + inicialização
│   └── backup.py        # Backup/restore via GitHub Releases
├── etl/
│   ├── loader.py        # Leitura de arquivos (CSV/XLSX/XLS)
│   ├── cleaner.py       # Mapeamento de colunas, parsing de valores BRL, filtragem
│   ├── enricher.py      # Colunas derivadas: imposto, total_liquido, margem
│   └── pipeline.py      # Orquestrador: arquivo → banco de dados
├── analytics/
│   ├── kpis.py          # Todas as queries SQL → DataFrames
│   ├── abc.py           # Algoritmo Pareto ABC
│   └── classificacao.py # Lógica dos 5 status
└── utils/
    └── excel_export.py  # Exportação Excel estilizada com openpyxl

tests/
├── unit/                # 7 módulos, testes de funções puras
└── integration/         # Testes de banco, pipeline e queries de KPI
```

**Armazenamento:** SQLite com modo WAL. Cada linha em `fato_vendas` representa um SKU em um período, com constraint `UNIQUE(data_referencia, sku, fonte)` que torna reimportações idempotentes. O banco é salvo no GitHub Releases a cada ingestão.

**Por que SQLite:** O volume de dados é previsível e limitado (centenas de SKUs, cadência mensal). SQLite elimina overhead operacional sem abrir mão da expressividade de queries. O modo WAL permite leituras concorrentes durante escritas — relevante no contexto Streamlit.

**Design do ETL:** Cada etapa é uma função pura — `load_file → clean → enrich`. O cleaner trata a ambiguidade do formato numérico brasileiro (`"1.234,56"` vs `"1,234.56"` vs `"-"` vs `None`) em uma única função `limpar_valor()` bem testada. O enricher recalcula imposto, margem líquida e margem bruta do zero, sem confiar nas colunas derivadas do arquivo fonte — intencional, dado que a planilha original tinha erros de fórmula.

### A Fórmula

```
total_liquido = receita - frete - comissao - (receita × 25,59%) - custo_produto + incentivo
margem = total_liquido / receita
```

**Por que 25,59% é fixo:** O gestor calculou a alíquota composta de PIS, COFINS, ICMS e variações estaduais aplicáveis à operação e fixou a soma máxima possível da tabela como taxa base. A lógica é conservadora por design: se o imposto real for menor, a margem real é *melhor* do que a exibida — nunca vai aparecer lucro onde existe prejuízo. Errar para menos no imposto significa errar para cima na margem, o que geraria decisões equivocadas. Errar para mais no imposto é seguro.

Essa fórmula foi validada contra a planilha do gestor. O sistema é mais preciso: a planilha tinha referências quebradas excluindo frete e incentivos de 29 produtos. Para os 50 produtos onde a fórmula estava correta, os valores são idênticos até a precisão de ponto flutuante.

### Testes

```
183 testes · 99% de cobertura de código
```

| Módulo | Cobertura |
|--------|-----------|
| analytics/abc.py | 100% |
| analytics/classificacao.py | 100% |
| analytics/kpis.py | 100% |
| db/connection.py | 100% |
| db/schema.py | 100% |
| etl/cleaner.py | 100% |
| etl/enricher.py | 100% |
| etl/pipeline.py | 100% |
| utils/excel_export.py | 100% |
| etl/loader.py | 95% |

Testes unitários cobrem todos os edge cases de parsing: `None`, `NaN`, strings vazias, formato BRL, formato americano, valores negativos, negativos entre parênteses. Testes de integração rodam em SQLite isolado no `tmp_path` — dados de produção nunca são tocados.

Um bug real foi encontrado durante o desenvolvimento dos testes: `pipeline._upsert` capturava `Exception` genericamente em vez de `sqlite3.IntegrityError`, silenciando qualquer erro de banco de dados (schema incompatível, disco cheio) e incrementando `rows_skipped` falsamente.

```bash
python -m pytest tests/ --cov=src --cov-config=.coveragerc
```

### Stack

| Camada | Tecnologia |
|--------|------------|
| Frontend | Streamlit 1.50 |
| Dados | pandas, SQLite (WAL) |
| Gráficos | Plotly Express |
| Exportação Excel | openpyxl (estilizado: headers navy, escalas de cor, freeze panes, auto-filter) |
| ETL | Python puro — sem Spark, sem Airflow, sem overhead |
| Testes | pytest + pytest-cov |
| Hospedagem | Streamlit Community Cloud |
| Backup do DB | GitHub Releases |

### Rodando Localmente

Requer Python 3.10+.

```bash
git clone https://github.com/nauticarefrigeracao-ti/streamlit-app.git
cd streamlit-app
pip install -r requirements.txt
streamlit run app/main.py
```

No Windows, clique duas vezes em `Iniciar.bat` — instala Python e todas as dependências automaticamente na primeira execução.

### Próximos Passos

- Camada de autenticação (login e senha por usuário)
- Suporte multi-canal (isolando margens do Mercado Livre vs. Shopee vs. venda direta)
- Ingestão mensal automatizada via pipeline agendado
- Módulo de previsão de tendência de margem

---

*Desenvolvido por [Lucas Leite Gonzales](mailto:nauticarefrigeracao.ti@gmail.com) — desenvolvimento solo, da descoberta de negócio ao design do ETL, lógica analítica, interface, testes e deploy.*

---
---

<a name="english"></a>
## 🇺🇸 English

A business intelligence dashboard that replaced a manual daily Excel routine with an automated, interactive margin and revenue analysis system — built solo from discovery to production.

### The Problem

The operations manager at Grupo Náutica Refrigeração spent significant time every day manually updating a spreadsheet to track product margin and revenue performance across their Mercado Livre catalog. The spreadsheet had broken cell references on 29 of 79 products — some excluding freight reimbursements from the formula, others excluding incentives. Decisions on pricing, stock priority, and product discontinuation were being made on unreliable data.

The goal: automate the entire process, fix the formula errors, and deliver actionable insights through a self-serve dashboard that non-technical stakeholders can use without depending on IT.

### What It Does

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

### Architecture

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

**Why SQLite:** The data volume is predictable and bounded (hundreds of SKUs, monthly cadence). SQLite eliminates operational overhead without sacrificing query expressiveness. WAL mode allows concurrent reads during writes, which matters in a Streamlit multi-session context.

**ETL design:** Each stage is a pure function — `load_file → clean → enrich`. The cleaner handles the BRL number format ambiguity (`"1.234,56"` vs `"1,234.56"` vs `"-"` vs `None`) with a single well-tested `limpar_valor()` function. The enricher recalculates tax, net margin, and gross margin from scratch rather than trusting the source file's derived columns — this is intentional, since the original spreadsheet had formula errors.

### The Formula

```
total_liquido = receita - frete - comissao - (receita × 25.59%) - custo_produto + incentivo
margem = total_liquido / receita
```

**Why 25.59% is fixed:** The manager calculated the composite rate of PIS, COFINS, ICMS and applicable state tax variations, then set the highest possible total from the table as the base rate. The logic is deliberately conservative: if the real tax is lower, the real margin is *better* than displayed — profit will never appear where there is loss. Underestimating tax means overestimating margin, which leads to bad decisions. Overestimating tax is safe.

This formula was validated against the manager's Excel file. The system is more accurate: the original spreadsheet had broken references excluding freight and incentives from 29 products. For the 50 products where the Excel formula was correct, values match to floating-point precision.

### Tests

```
183 tests · 99% code coverage
```

| Module | Coverage |
|--------|----------|
| analytics/abc.py | 100% |
| analytics/classificacao.py | 100% |
| analytics/kpis.py | 100% |
| db/connection.py | 100% |
| db/schema.py | 100% |
| etl/cleaner.py | 100% |
| etl/enricher.py | 100% |
| etl/pipeline.py | 100% |
| utils/excel_export.py | 100% |
| etl/loader.py | 95% |

Unit tests cover all parsing edge cases: `None`, `NaN`, empty strings, BRL format, US format, negative values, parenthetical negatives. Integration tests run against an isolated SQLite instance in `tmp_path` — production data is never touched.

A real bug was caught during test development: `pipeline._upsert` was catching `Exception` broadly instead of `sqlite3.IntegrityError`, silently swallowing any database error (schema mismatch, disk full) and incrementing `rows_skipped` falsely.

```bash
python -m pytest tests/ --cov=src --cov-config=.coveragerc
```

### Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit 1.50 |
| Data | pandas, SQLite (WAL) |
| Charts | Plotly Express |
| Excel export | openpyxl (styled: navy headers, color scales, freeze panes, auto-filter) |
| ETL | Pure Python — no Spark, no Airflow, no overhead |
| Tests | pytest + pytest-cov |
| Hosting | Streamlit Community Cloud |
| DB backup | GitHub Releases |

### Running Locally

Requires Python 3.10+.

```bash
git clone https://github.com/nauticarefrigeracao-ti/streamlit-app.git
cd streamlit-app
pip install -r requirements.txt
streamlit run app/main.py
```

On Windows, double-click `Iniciar.bat` — it installs Python and all dependencies automatically on first run.

### What's Next

- Authentication layer (login/password per user)
- Multi-channel support (isolating Mercado Livre vs. Shopee vs. direct sales margins)
- Automated monthly ingestion via scheduled pipeline
- Forecasting module for margin trend projection

---

*Built by [Lucas Leite Gonzales](mailto:nauticarefrigeracao.ti@gmail.com) — solo development, from business discovery through ETL design, analytics logic, UI, testing, and deployment.*
