"""Curva ABC — múltiplas perspectivas: faturamento, lucro e custo."""

import plotly.express as px
import streamlit as st

from ntc_theme import data_table
from src.analytics.abc import calcular_abc, resumo_abc
from src.analytics.kpis import get_vendas
from src.utils.excel_export import to_excel_styled

_NAVY  = "#14283C"
_GREEN = "#1F7A3A"
_AMBER = "#C8901C"
_GRAY  = "#9BACBD"
_RED   = "#B5322B"

ABC_COLORS  = {"A": _GREEN, "B": _AMBER, "C": _GRAY}

_ABC_BADGE = {
    "A": ("#E8F5E9", "#1F7A3A"),
    "B": ("#FFF8E1", "#C8901C"),
    "C": ("#F1F1F1", "#737373"),
}

_PERSPECTIVAS = {
    "Faturamento Bruto":     ("receita_total",  "Receita Bruta (R$)"),
    "Lucro (Total Líquido)": ("total_liquido",  "Total Líquido (R$)"),
    "Custo do Produto":      ("custo_produto",  "Custo Produto (R$)"),
}

_LABELS = {
    "A": "Classe A — Top 80%",
    "B": "Classe B — 80–95%",
    "C": "Classe C — Cauda",
}

_DESCRICOES = {
    "A": "Poucos produtos, grande impacto. Prioridade máxima: estoque, negociação, campanhas.",
    "B": "Produtos intermediários. Monitorar crescimento — podem migrar para A ou cair para C.",
    "C": "Longa cauda. Avaliar custo de manutenção vs. contribuição marginal.",
}

_TOOLTIPS_ABC = {
    "A": (
        "Esses produtos são o coração do negócio — concentram 80% do resultado. "
        "Nunca deixe o estoque zerar: uma ruptura aqui impacta diretamente o faturamento. "
        "Priorize negociação de custo com fornecedores desses itens e monitore a margem todo mês. "
        "Uma queda de margem num produto Classe A afeta o negócio inteiro."
    ),
    "B": (
        "Produtos com potencial — podem crescer para Classe A ou regredir para C. "
        "Identifique os de maior margem: uma campanha ou melhoria de anúncio pode transformá-los em Estrela. "
        "Fique atento aos que estão caindo de volume — podem estar perdendo relevância no mercado."
    ),
    "C": (
        "São muitos produtos mas representam apenas 5% do faturamento. "
        "Cada um ocupa capital de giro e atenção operacional. "
        "Avalie: os de boa margem valem o esforço. Os de margem baixa são candidatos a corte — "
        "manter produto C com margem ruim custa mais do que rende."
    ),
}

_COLS_ABC = [
    {"key": "abc",          "label": "Classe",       "type": "badge", "colors": _ABC_BADGE, "width": "70px",
     "help": "Classificação ABC — A = top 80% da receita · B = 80–95% · C = cauda"},
    {"key": "sku",          "label": "SKU",          "type": "mono",  "width": "90px"},
    {"key": "produto",      "label": "Produto"},
    {"key": "Custo Produto","label": "Custo Produto","align": "right",
     "help": "CMV — custo de aquisição pago ao fornecedor"},
    {"key": "Margem %",     "label": "Margem %",     "type": "margem", "align": "right",
     "help": "% do preço de venda que vira lucro após todos os custos"},
    {"key": "% Acum.",      "label": "% Acum.",      "align": "right",
     "help": "% acumulado de receita até este produto no ranking — ex.: 45% = este produto e os acima dele somam 45% da receita total"},
]


def render(periodo: str, filtro_sku: str = "") -> None:
    df_raw = get_vendas(periodo)
    n_total = len(df_raw)

    st.caption(
        "A análise ABC classifica produtos pelo princípio de Pareto (80/20): "
        "poucos produtos (Classe A) geram a maior parte do resultado. "
        "Use para priorizar estoque, negociações e ações comerciais."
    )

    # ── Perspectiva ───────────────────────────────────────────────────────────
    perspectiva = st.radio(
        "Perspectiva da curva ABC",
        list(_PERSPECTIVAS.keys()),
        horizontal=True,
        key="abc_visao",
    )
    coluna, label_eixo = _PERSPECTIVAS[perspectiva]

    df_base = df_raw.copy()
    if coluna == "total_liquido":
        df_base = df_base[df_base["total_liquido"] > 0]

    df = calcular_abc(df_base, coluna=coluna)
    df = _filtrar(df, filtro_sku)
    n_filtrado = len(df)

    if df.empty:
        st.warning(f"Nenhum produto encontrado para **'{filtro_sku}'**. Tente outro SKU ou limpe o filtro no painel lateral.")
        return

    res = resumo_abc(df)
    _nota_filtro(filtro_sku, n_filtrado, n_total)

    # ── Cards A / B / C ───────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    for col, (_, row) in zip([c1, c2, c3], res.iterrows()):
        cor = ABC_COLORS[row["abc"]]
        tip = _TOOLTIPS_ABC[row["abc"]]
        with col:
            st.markdown(
                f"""
                <div style="background:#fff;border:1px solid #E4E4E4;
                            border-left:4px solid {cor};border-radius:12px;
                            padding:1.1rem 1.4rem;
                            box-shadow:0 1px 3px rgba(20,40,60,0.06);">
                  <p style="color:#525252;font-size:0.70rem;letter-spacing:0.08em;
                             text-transform:uppercase;font-weight:600;margin:0 0 0.3rem">
                    {_LABELS[row['abc']]}
                    <span style="color:#9BACBD;font-size:11px;font-style:normal;
                                 cursor:help;font-weight:400;"
                          title="{tip}">ⓘ</span>
                  </p>
                  <p style="font-family:'Rajdhani',sans-serif;font-weight:700;
                             font-size:1.65rem;color:{_NAVY};margin:0 0 0.15rem">
                    {int(row['qtd_skus'])} SKUs
                  </p>
                  <p style="font-size:0.80rem;color:#525252;margin:0 0 0.4rem">
                    {row['pct_receita']*100:.1f}% do total
                    &nbsp;·&nbsp; {_brl(row['receita'])}
                  </p>
                  <p style="font-size:0.72rem;color:#737373;font-style:italic;margin:0">
                    {_DESCRICOES[row['abc']]}
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Treemap ───────────────────────────────────────────────────────────────
    _perspectiva_label = {
        "Faturamento Bruto":     "Faturamento Bruto",
        "Lucro (Total Líquido)": "Lucro Gerado",
        "Custo do Produto":      "Custo do Produto",
    }[perspectiva]

    st.markdown(
        f"<div style='text-align:center;font-family:\"Source Sans Pro\",sans-serif;"
        f"font-weight:600;font-size:1.45rem;color:#14283C;line-height:1.3;"
        f"margin:0 0 0.2rem'>Quem ocupa mais espaço no seu portfólio?</div>"
        f"<p style='text-align:center;font-size:0.82rem;color:#525252;margin:0 0 0.75rem'>"
        f"Cada bloco é um produto — quanto maior, mais representa no <b>{_perspectiva_label}</b>. "
        f"<span style='color:{_GREEN};font-weight:600'>Verde = Classe A</span> (top 80%) &nbsp;·&nbsp; "
        f"<span style='color:{_AMBER};font-weight:600'>Dourado = Classe B</span> (80–95%) &nbsp;·&nbsp; "
        f"<span style='color:{_GRAY};font-weight:600'>Cinza = Classe C</span> (cauda). "
        f"Passe o mouse sobre qualquer bloco para ver os detalhes.</p>",
        unsafe_allow_html=True,
    )

    fig_tree = px.treemap(
        df,
        path=["abc", "sku"],
        values=coluna,
        color="abc",
        color_discrete_map=ABC_COLORS,
        custom_data=["produto", "margem", coluna],
    )
    fig_tree.update_traces(
        textfont_size=11,
        marker=dict(line=dict(width=2, color="white")),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "%{customdata[0]}<br>"
            f"{label_eixo}: R$ %{{customdata[2]:,.2f}}<br>"
            "Margem: %{customdata[1]:.1%}"
            "<extra></extra>"
        ),
    )
    fig_tree.update_layout(
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        font_color=_NAVY,
        margin=dict(l=0, r=0, t=10, b=0),
        height=520,
        showlegend=False,
    )
    st.plotly_chart(fig_tree, use_container_width=True)

    st.divider()

    # ── Tabela detalhada ───────────────────────────────────────────────────────
    st.subheader("Tabela detalhada")

    busca_col, sort_col, exp_col = st.columns([2, 2, 1])
    with busca_col:
        busca = st.text_input(
            "busca_abc",
            placeholder="🔍  Buscar SKU ou produto...",
            label_visibility="collapsed",
            key="abc_busca_local",
        )
    with sort_col:
        _SORT_OPTS = {
            "Ranking ABC (padrão)": ("perc_acumulado",  True),
            "Custo Produto ↓":      ("custo_produto",   False),
            "Margem % ↓":           ("margem",          False),
            "Margem % ↑":           ("margem",          True),
            "Produto A→Z":          ("produto",         True),
        }
        sort_key = st.selectbox("Ordenar por", list(_SORT_OPTS.keys()),
                                key="abc_sort", label_visibility="collapsed")
    with exp_col:
        st.download_button(
            "📥 Exportar Excel",
            data=_to_excel(df),
            file_name=f"abc_{perspectiva.split()[0].lower()}_{periodo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    _sort_col, _sort_asc = _SORT_OPTS[sort_key]
    df_show = _filtrar(df, busca).sort_values(_sort_col, ascending=_sort_asc)

    display = df_show[[
        "abc", "sku", "produto",
        "custo_produto", "margem", "perc_acumulado",
    ]].copy()
    display.columns = [
        "abc", "sku", "produto",
        "Custo Produto", "Margem %", "% Acum.",
    ]
    display["Custo Produto"]  = display["Custo Produto"].map(_brl)
    display["Margem %"]       = display["Margem %"].map(_pct)
    display["% Acum."]        = display["% Acum."].map(lambda v: f"{v*100:.1f}%")

    data_table(display, _COLS_ABC, height=520)



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


_ABC_COLS_EXCEL = [
    {"key": "abc",           "label": "Classe",             "fmt": "text",    "width": 9,  "total": False},
    {"key": "sku",           "label": "SKU",                "fmt": "text",    "width": 13},
    {"key": "produto",       "label": "Produto",            "fmt": "text",    "width": 42},
    {"key": "receita_total", "label": "Receita Bruta (R$)", "fmt": "brl"},
    {"key": "custo_produto", "label": "Custo Produto (R$)", "fmt": "brl"},
    {"key": "total_liquido", "label": "Total Líquido (R$)", "fmt": "brl"},
    {"key": "margem",        "label": "Margem %",           "fmt": "pct"},
    {"key": "perc_acumulado","label": "% Acumulado",        "fmt": "pct",     "total": False},
]


def _to_excel(df) -> bytes:
    return to_excel_styled(df, _ABC_COLS_EXCEL, sheet_name="Curva ABC")


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
