"""Classificação de produtos — scatter matrix + box plot + cards + tabelas por status."""

import plotly.express as px
import streamlit as st

from ntc_theme import data_table
from src.utils.excel_export import to_excel_styled
from src.analytics.classificacao import (
    STATUS_COLORS, STATUS_DESC, STATUS_ICONS, STATUS_TOOLTIP,
    classificar, resumo_classificacao,
)
from src.analytics.kpis import get_vendas

_NAVY = "#14283C"

_STATUS_ORDER = ["Estrela", "Volume Cego", "Oportunidade", "Parado", "Problema"]

_COLS_STATUS = [
    {"key": "sku",          "label": "SKU",          "type": "mono", "width": "90px",
     "help": "Código de identificação único do produto"},
    {"key": "produto",      "label": "Produto",
     "help": "Nome completo do produto"},
    {"key": "Receita Bruta","label": "Receita Bruta","align": "right",
     "help": "Valor total faturado antes de descontar qualquer custo"},
    {"key": "Total Líquido","label": "Total Líquido","align": "right",
     "help": "O que sobra após descontar imposto, frete, comissão e custo do produto"},
    {"key": "Margem %",     "label": "Margem %",     "type": "margem", "align": "right",
     "help": "% do preço de venda que vira lucro. Vermelho < 5% · Azul 5–15% · Verde ≥ 15%"},
]

# Sort padrão por status — cada grupo tem uma lógica de prioridade diferente
_SORT_OPTS_POR_STATUS = {
    "Estrela": {
        "Maior lucro 1° (Total Líquido ↓)": ("total_liquido", False),
        "Receita Bruta ↓":                  ("receita_total", False),
        "Margem % ↓":                       ("margem",        False),
        "Produto A→Z":                      ("produto",       True),
    },
    "Volume Cego": {
        "Maior receita 1° (Receita Bruta ↓)": ("receita_total", False),
        "Margem % ↑":                          ("margem",        True),
        "Total Líquido ↓":                     ("total_liquido", False),
        "Produto A→Z":                         ("produto",       True),
    },
    "Oportunidade": {
        "Maior margem 1° (Margem % ↓)": ("margem",        False),
        "Receita Bruta ↓":              ("receita_total", False),
        "Total Líquido ↓":              ("total_liquido", False),
        "Produto A→Z":                  ("produto",       True),
    },
    "Parado": {
        "Maior estoque parado 1° (Receita Bruta ↓)": ("receita_total", False),
        "Total Líquido ↓":                            ("total_liquido", False),
        "Margem % ↓":                                 ("margem",        False),
        "Produto A→Z":                                ("produto",       True),
    },
    "Problema": {
        "Maior perda 1° (Total Líquido ↑)": ("total_liquido", True),
        "Receita Bruta ↓":                  ("receita_total", False),
        "Margem % ↑":                       ("margem",        True),
        "Produto A→Z":                      ("produto",       True),
    },
}


def render(periodo: str, filtro_sku: str = "") -> None:
    df_raw = get_vendas(periodo)
    n_total = len(df_raw)
    df = classificar(df_raw)
    df = _filtrar(df, filtro_sku)

    if df.empty:
        st.warning(f"Nenhum produto encontrado para '{filtro_sku}'.")
        return

    _nota_filtro(filtro_sku, len(df), n_total)
    res = resumo_classificacao(df)

    # ── Scatter ───────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='text-align:center;font-family:\"Source Sans Pro\",sans-serif;"
        "font-weight:600;font-size:1.45rem;color:#14283C;line-height:1.3;"
        "margin:0 0 0.2rem'>Onde cada produto está no portfólio?</div>"
        "<p style='text-align:center;font-size:0.82rem;color:#525252;margin:0 0 0.6rem'>"
        "Cada círculo é um produto — quanto maior, mais vende. "
        "As linhas tracejadas marcam a mediana do portfólio (receita e margem). "
        "Produtos no canto superior direito têm alta receita <em>e</em> boa margem — são as <strong>Estrelas</strong>."
        "</p>",
        unsafe_allow_html=True,
    )

    fig = px.scatter(
        df,
        x="receita_total",
        y="margem",
        color="status",
        size="receita_total",
        size_max=40,
        hover_name="produto",
        hover_data={
            "sku": True,
            "receita_total": ":,.2f",
            "total_liquido": ":,.2f",
            "margem": ":.1%",
            "status": False,
        },
        color_discrete_map=STATUS_COLORS,
        labels={
            "receita_total": "Receita Bruta (R$)",
            "margem": "Margem (%)",
            "status": "Status",
            "total_liquido": "Total Líquido (R$)",
        },
        category_orders={"status": _STATUS_ORDER},
    )
    med_r = df["receita_total"].median()
    med_m = df[df["margem"] >= 0]["margem"].median()
    fig.add_vline(x=med_r, line_dash="dot", line_color="#9BACBD", line_width=1.5,
                  annotation_text="Mediana receita", annotation_position="top right",
                  annotation_font_size=9, annotation_font_color="#9BACBD")
    fig.add_hline(y=med_m, line_dash="dot", line_color="#9BACBD", line_width=1.5,
                  annotation_text="Mediana margem", annotation_position="top right",
                  annotation_font_size=9, annotation_font_color="#9BACBD")
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font_family="Inter, sans-serif", font_color=_NAVY,
        yaxis_tickformat=".0%",
        xaxis_tickprefix="R$ ",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=10, t=40, b=30),
        height=480,
    )
    st.plotly_chart(fig, use_container_width=True)


    st.divider()

    # ── Cards por status ──────────────────────────────────────────────────────
    st.subheader("Resumo por status")
    res_indexed = res.set_index("status")
    cols = st.columns(len(_STATUS_ORDER))

    for col, status in zip(cols, _STATUS_ORDER):
        if status not in res_indexed.index:
            with col:
                cor = STATUS_COLORS[status]
                st.markdown(
                    f"<div style='background:#fff;border:1px solid #E4E4E4;"
                    f"border-left:4px solid {cor};border-radius:12px;"
                    f"padding:0.9rem 1.1rem;opacity:0.5'>"
                    f"<p style='color:#525252;font-size:0.68rem;letter-spacing:0.08em;"
                    f"text-transform:uppercase;font-weight:600;margin:0 0 0.2rem'>"
                    f"{STATUS_ICONS[status]} {status}</p>"
                    f"<p style='font-family:Rajdhani;font-size:1.4rem;font-weight:700;"
                    f"color:{_NAVY};margin:0'>0 SKUs</p></div>",
                    unsafe_allow_html=True,
                )
            continue
        row = res_indexed.loc[status]
        cor  = STATUS_COLORS[status]
        icon = STATUS_ICONS[status]
        tip  = STATUS_TOOLTIP[status]
        with col:
            st.markdown(
                f"""
                <div style="background:#fff;border:1px solid #E4E4E4;
                            border-left:4px solid {cor};border-radius:12px;
                            padding:1rem 1.2rem;
                            box-shadow:0 1px 3px rgba(20,40,60,0.06);">
                  <p style="color:#525252;font-size:0.68rem;letter-spacing:0.08em;
                             text-transform:uppercase;font-weight:600;margin:0 0 0.25rem">
                    {icon} {status}
                    <span style="color:#9BACBD;font-size:11px;font-style:normal;
                                 cursor:help;font-weight:400;"
                          title="{tip}">ⓘ</span>
                  </p>
                  <p style="font-family:'Rajdhani',sans-serif;font-weight:700;
                             font-size:1.50rem;color:{_NAVY};margin:0 0 0.1rem">
                    {int(row['qtd'])} SKUs
                  </p>
                  <p style="font-size:0.76rem;color:#525252;margin:0 0 0.25rem">
                    {_brl(row['receita'])}
                    &nbsp;·&nbsp; margem média {_pct(row['margem_media'])}
                  </p>
                  <p style="font-size:0.68rem;color:#737373;margin:0;font-style:italic;
                             line-height:1.35">
                    {STATUS_DESC[status]}
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Tabelas por status ────────────────────────────────────────────────────
    st.subheader("Produtos por status")

    for status in _STATUS_ORDER:
        subset = df[df["status"] == status].copy()
        if subset.empty:
            continue
        cor  = STATUS_COLORS[status]
        icon = STATUS_ICONS[status]
        with st.expander(
            f"{icon} {status} — {len(subset)} produto{'s' if len(subset) > 1 else ''}",
            expanded=(status == "Problema"),
        ):
            _SORT_OPTS = _SORT_OPTS_POR_STATUS[status]
            exp_col, sort_col, _ = st.columns([1, 2, 3])
            with exp_col:
                st.download_button(
                    "📥 Excel",
                    data=_to_excel(subset, status),
                    file_name=f"classificacao_{status.lower().replace(' ', '_')}_{periodo}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"exp_{status}",
                )
            with sort_col:
                sort_key = st.selectbox("Ordenar por", list(_SORT_OPTS.keys()),
                                        key=f"sort_{status}", label_visibility="collapsed")

            _sc, _sa = _SORT_OPTS[sort_key]
            display = subset[[
                "sku", "produto", "receita_total", "total_liquido", "margem"
            ]].sort_values(_sc, ascending=_sa).copy()
            display.columns = ["sku", "produto", "Receita Bruta", "Total Líquido", "Margem %"]
            display["Receita Bruta"]  = display["Receita Bruta"].map(_brl)
            display["Total Líquido"]  = display["Total Líquido"].map(_brl)
            display["Margem %"]       = display["Margem %"].map(_pct)

            data_table(display, _COLS_STATUS, height=320)


def _filtrar(df, q: str):
    if not q or not q.strip():
        return df
    q = q.strip().lower()
    mask = (
        df["sku"].str.lower().str.contains(q, na=False) |
        df["produto"].str.lower().str.contains(q, na=False)
    )
    return df[mask]


def _nota_filtro(filtro: str, n_fil: int, n_tot: int) -> None:
    if filtro and filtro.strip():
        st.caption(f"Filtro global ativo: **'{filtro}'** — {n_fil} de {n_tot} produtos.")


_CLASS_COLS_EXCEL = [
    {"key": "sku",           "label": "SKU",                "fmt": "text", "width": 13},
    {"key": "produto",       "label": "Produto",            "fmt": "text", "width": 42},
    {"key": "receita_total", "label": "Receita Bruta (R$)", "fmt": "brl"},
    {"key": "total_liquido", "label": "Total Líquido (R$)", "fmt": "brl"},
    {"key": "custo_produto", "label": "Custo Produto (R$)", "fmt": "brl"},
    {"key": "margem",        "label": "Margem %",           "fmt": "pct"},
]


def _to_excel(df, sheet_name: str) -> bytes:
    return to_excel_styled(df, _CLASS_COLS_EXCEL, sheet_name=sheet_name[:31])


def _brl(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def _pct(v) -> str:
    try:
        return f"{float(v) * 100:.1f}%"
    except Exception:
        return "—"
