"""Visão Geral — KPIs, composição de custos, top produtos, tabela completa."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ntc_theme import data_table
from src.analytics.classificacao import STATUS_DESC, classificar
from src.analytics.kpis import get_composicao_custos, get_kpis, get_vendas
from src.utils.excel_export import to_excel_styled

_NAVY  = "#14283C"
_GOLD  = "#BFA168"
_GREEN = "#1F7A3A"
_AMBER = "#C8901C"
_RED   = "#B5322B"
_BLUE  = "#2E6FA8"
_GRAY  = "#9BACBD"

_STATUS_COLORS = {
    "Estrela":      ("#E8F5E9", "#1F7A3A"),
    "Volume Cego":  ("#E7EBF0", "#14283C"),
    "Oportunidade": ("#FFF8E1", "#C8901C"),
    "Parado":       ("#F1F1F1", "#737373"),
    "Problema":     ("#FFEBEE", "#B5322B"),
}

# Urgência de ação: Problema (perde dinheiro) → Volume Cego (risco de receita) → Parado (decisão pendente) → Oportunidade → Estrela
_STATUS_RANK = {"Problema": 0, "Volume Cego": 1, "Parado": 2, "Oportunidade": 3, "Estrela": 4}

_COLS_MAIN = [
    {"key": "sku",           "label": "SKU",           "type": "mono",  "width": "90px",
     "help": "Código de identificação único do produto no sistema"},
    {"key": "produto",       "label": "Produto",
     "help": "Nome completo do produto conforme cadastrado"},
    {"key": "status",        "label": "Status",        "type": "badge", "colors": _STATUS_COLORS,
     "tooltips": STATUS_DESC, "width": "110px",
     "help": "Classificação estratégica. Passe o mouse sobre o badge colorido para ver o que cada status significa."},
    {"key": "Receita Bruta", "label": "Receita Bruta", "align": "right",
     "help": "Valor total faturado no período, antes de descontar qualquer custo ou imposto"},
    {"key": "Total Líquido", "label": "Total Líquido", "align": "right",
     "help": "O que sobra para a empresa após descontar: imposto + frete + comissão Mercado Livre + custo do produto"},
    {"key": "Margem %",      "label": "Margem",        "type": "margem", "align": "right",
     "help": "% do preço de venda que vira lucro. Ex.: 20% = a cada R$ 100 vendido, R$ 20 é lucro. Vermelho < 5% · Azul 5–15% · Verde ≥ 15%"},
    {"key": "Margem Média",  "label": "Margem Média",  "type": "margem", "align": "right",
     "help": "Média histórica de margem deste produto em todos os meses já importados no sistema"},
    {"key": "Δ vs. Média",   "label": "Δ vs. Média",   "type": "delta",  "align": "right",
     "help": "Diferença entre a margem atual e a média histórica. (+) = está melhor que o normal · (−) = está pior"},
    {"key": "Frete",         "label": "Frete",         "align": "right",
     "help": "Custo total de frete cobrado pelo Mercado Livre neste produto no período"},
    {"key": "Comissão ML",   "label": "Comissão ML",   "align": "right",
     "help": "Taxa cobrada pelo Mercado Livre sobre cada venda realizada (percentual sobre a Receita Bruta)"},
    {"key": "Imposto",       "label": "Imposto",       "align": "right",
     "help": "Impostos incidentes sobre a Receita Bruta conforme o regime tributário da empresa"},
    {"key": "Custo Produto", "label": "Custo Produto", "align": "right",
     "help": "Custo de aquisição do produto pago ao fornecedor — também chamado de CMV (Custo da Mercadoria Vendida)"},
]

_COLS_HIGHLIGHT = [
    {"key": "sku",           "label": "SKU",          "type": "mono", "width": "90px",
     "help": "Código de identificação único do produto"},
    {"key": "produto",       "label": "Produto",
     "help": "Nome completo do produto"},
    {"key": "Receita Bruta", "label": "Receita Bruta","align": "right",
     "help": "Valor total faturado antes de descontar qualquer custo"},
    {"key": "Total Líquido", "label": "Total Líquido","align": "right",
     "help": "O que sobra após descontar todos os custos"},
    {"key": "Margem %",      "label": "Margem %",     "type": "margem", "align": "right",
     "help": "Percentual de lucro sobre o preço de venda"},
]


def render(periodo: str, filtro_sku: str = "") -> None:
    df_raw = get_vendas(periodo)
    df_all = classificar(df_raw)           # portfólio completo — KPIs sempre daqui
    n_total = len(df_all)

    df = _filtrar(df_all, filtro_sku)      # subset para tabelas/charts

    if df.empty:
        st.warning(f"Nenhum produto encontrado para '{filtro_sku}'.")
        return

    med_margem = df_all[df_all["margem"] >= 0]["margem"].median()

    # ── KPIs — sempre do portfólio completo ───────────────────────────────────
    fat_bruto    = df_all["receita_total"].sum()
    fat_liquido  = df_all["total_liquido"].sum()
    margem_g     = fat_liquido / fat_bruto if fat_bruto else 0
    margem_media = df_all["margem"].mean()
    n_skus       = len(df_all)
    n_prej       = int((df_all["margem"] < 0).sum())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Faturamento Bruto", _brl(fat_bruto),
              help="Soma de todas as receitas do período, antes de descontar qualquer custo.")
    c2.metric("Total Líquido", _brl(fat_liquido),
              help="O que sobra no caixa após pagar imposto, frete, comissão do Mercado Livre e custo dos produtos. É o lucro real do período.")
    c3.metric("Margem Global", _pct(margem_g),
              help="Percentual do faturamento total que virou lucro. Produtos que mais faturam pesam mais neste número. Use para avaliar a saúde geral do negócio.")
    c4.metric("Margem Média", _pct(margem_media),
              help="Média simples da margem de cada produto, sem considerar quanto cada um faturou. Um produto pequeno com margem alta puxa este número para cima sem impacto real no caixa. Compare sempre com a Margem Global.")
    c5.metric("SKUs no período", str(n_skus),
              help="Quantidade de produtos diferentes com vendas registradas neste mês.")
    c6.metric("SKUs com prejuízo", str(n_prej),
              delta=f"−{n_prej}" if n_prej else None,
              delta_color="inverse",
              help="Produtos que custaram mais do que renderam — custo + frete + comissão + imposto superou a receita. Cada um está tirando dinheiro do negócio.")

    st.divider()

    # ── Composição de custos + Top 20 ─────────────────────────────────────────
    col_donut, col_bar = st.columns([1, 1], gap="large")

    with col_donut:
        viz_left = st.session_state.get("dash_viz_left", "Donut")
        _donut_title = "Para onde vai cada R$ 1,00" if viz_left == "Donut" else "Cascata de resultado"
        st.markdown(
            f"<div style='text-align:center;font-family:\"Source Sans Pro\",sans-serif;"
            f"font-weight:600;font-size:1.45rem;color:#14283C;line-height:1.3;"
            f"margin:0 0 0.4rem'>{_donut_title}</div>",
            unsafe_allow_html=True,
        )

        if viz_left == "Donut":
            comp = get_composicao_custos(periodo)
            fig_donut = go.Figure(go.Pie(
                labels=list(comp.keys()),
                values=[v * 100 for v in comp.values()],
                hole=0.54,
                marker_colors=[_RED, _GRAY, _AMBER, _BLUE, _GREEN],
                textinfo="percent",
                textfont_size=11,
                hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            ))
            fig_donut.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.18,
                            xanchor="center", x=0.5,
                            font=dict(size=10, color=_NAVY)),
                margin=dict(l=10, r=10, t=10, b=70),
                paper_bgcolor="white",
                height=370,
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            tot_imposto   = df_all["imposto"].sum()
            tot_frete     = df_all["frete"].sum()
            tot_comissao  = df_all["comissao_ml"].sum()
            tot_custo     = df_all["custo_produto"].sum()
            tot_incentivo = df_all["incentivo"].sum() if "incentivo" in df_all.columns else 0.0
            pct_imp       = tot_imposto / fat_bruto * 100 if fat_bruto else 0
            _wf_x = ["Receita Bruta", f"Imposto ({pct_imp:.1f}%)", "Frete",
                     "Comissão ML", "Custo Produto"]
            _wf_m = ["absolute", "relative", "relative", "relative", "relative"]
            _wf_y = [fat_bruto, -tot_imposto, -tot_frete, -tot_comissao, -tot_custo]
            _wf_t = [_brl(fat_bruto), _brl(tot_imposto), _brl(tot_frete),
                     _brl(tot_comissao), _brl(tot_custo)]
            if tot_incentivo > 0:
                _wf_x.append("Incentivo ML")
                _wf_m.append("relative")
                _wf_y.append(tot_incentivo)
                _wf_t.append(_brl(tot_incentivo))
            _wf_x.append("Total Líquido")
            _wf_m.append("total")
            _wf_y.append(0)
            _wf_t.append(_brl(fat_liquido))
            fig_wf = go.Figure(go.Waterfall(
                orientation="v", measure=_wf_m, x=_wf_x, y=_wf_y, text=_wf_t,
                textposition="outside", textfont=dict(size=8),
                increasing=dict(marker_color=_GREEN),
                decreasing=dict(marker_color=_RED),
                totals=dict(marker_color=_BLUE),
                connector=dict(line=dict(color=_GRAY, width=0.8, dash="dot")),
            ))
            fig_wf.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="Inter, sans-serif", font_color=_NAVY,
                showlegend=False,
                margin=dict(l=10, r=10, t=10, b=30),
                height=370,
                yaxis=dict(tickprefix="R$ ", tickfont_size=8, showgrid=True,
                           gridcolor="#F0F0F0"),
                xaxis=dict(tickfont_size=8),
            )
            st.plotly_chart(fig_wf, use_container_width=True)

        # toggle ABAIXO do chart
        st.radio(
            "viz_esq", ["Donut", "Cascata"], horizontal=True,
            key="dash_viz_left", label_visibility="collapsed",
        )

    with col_bar:
        st.markdown(
            "<div style='text-align:center;font-family:\"Source Sans Pro\",sans-serif;"
            "font-weight:600;font-size:1.45rem;color:#14283C;line-height:1.3;"
            "margin:0 0 0.15rem'>Top 10 — Lucro gerado por produto</div>"
            "<p style='text-align:center;font-size:0.82rem;color:#525252;margin:0 0 0.5rem'>"
            "Quais produtos realmente colocam dinheiro no bolso, após todos os custos.</p>",
            unsafe_allow_html=True,
        )

        def _cat_margem(m):
            if m < 0.05:  return "< 5%"
            if m < 0.15:  return "5–15%"
            return "≥ 15%"

        top10 = df_all[df_all["total_liquido"] > 0].nlargest(10, "total_liquido").copy()
        top10["faixa"] = top10["margem"].apply(_cat_margem)
        top10["_label"] = top10["total_liquido"].apply(_brl)

        _BAR_COLORS = {"< 5%": _RED, "5–15%": _BLUE, "≥ 15%": _GREEN}
        _CAT_ORDER  = {"faixa": ["< 5%", "5–15%", "≥ 15%"]}

        fig_bar = px.bar(
            top10,
            x="total_liquido",
            y="sku",
            orientation="h",
            color="faixa",
            color_discrete_map=_BAR_COLORS,
            category_orders=_CAT_ORDER,
            labels={"total_liquido": "Total Líquido (R$)", "sku": "", "faixa": "Margem"},
            text="_label",
            custom_data=["receita_total", "margem", "produto"],
        )
        fig_bar.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_family="Inter, sans-serif", font_color=_NAVY,
            yaxis={"autorange": "reversed", "tickfont_size": 11},
            legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="right", x=1,
                        title_text="Margem", font=dict(size=10)),
            margin=dict(l=0, r=150, t=10, b=50),
            height=370,
        )
        fig_bar.update_traces(
            textposition="outside",
            textfont_size=10,
            cliponaxis=False,
            hovertemplate=(
                "<b>%{customdata[2]}</b><br>"
                "SKU: %{y}<br>"
                "Total Líquido: R$ %{x:,.2f}<br>"
                "Receita Bruta: R$ %{customdata[0]:,.2f}<br>"
                "Margem: %{customdata[1]:.1%}"
                "<extra></extra>"
            ),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ── Tabela principal ───────────────────────────────────────────────────────
    st.subheader("Todos os produtos")
    _nota_filtro(filtro_sku, len(df), n_total)

    busca_col, sort_col, toggle_col, exp_col = st.columns([2, 2, 1, 1])
    with busca_col:
        busca = st.text_input(
            "busca_local",
            placeholder="🔍  Buscar SKU ou produto...",
            label_visibility="collapsed",
            key="dash_busca_local",
        )
    with sort_col:
        _SORT_OPTS = {
            "Receita Bruta ↓":      ("receita_total", False),
            "Total Líquido ↓":      ("total_liquido", False),
            "Margem % ↓":           ("margem",        False),
            "Margem % ↑":           ("margem",        True),
            "Urgência (Problema 1°)": None,
            "Produto A→Z":          ("produto",       True),
        }
        sort_key = st.selectbox("Ordenar por", list(_SORT_OPTS.keys()),
                                key="dash_sort", label_visibility="collapsed")
    with toggle_col:
        show_costs = st.toggle("Custos", value=False, key="dash_show_costs",
                               help="Exibir colunas de Frete, Comissão, Imposto e Custo Produto")
    with exp_col:
        st.download_button(
            "📥 Exportar",
            data=_to_excel(df),
            file_name=f"visao_geral_{periodo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    df_show = _filtrar(df, busca).copy()
    df_show["vs_media"] = df_show["margem"] - med_margem
    if "margem_media" not in df_show.columns:
        df_show["margem_media"] = df_show["margem"]
    df_show["_rank"] = df_show["status"].map(_STATUS_RANK).fillna(99)
    if sort_key == "Urgência (Problema 1°)":
        df_show = df_show.sort_values(["_rank", "receita_total"], ascending=[True, False])
    else:
        _sort_col, _sort_asc = _SORT_OPTS[sort_key]
        df_show = df_show.sort_values(_sort_col, ascending=_sort_asc)

    if df_show.empty:
        st.info("Nenhum produto encontrado. Tente outro termo ou limpe o filtro no painel lateral.")
    else:
        display = df_show[[
            "sku", "produto", "status",
            "receita_total", "total_liquido", "margem", "margem_media", "vs_media",
            "frete", "comissao_ml", "imposto", "custo_produto",
        ]].copy()
        display.columns = [
            "sku", "produto", "status",
            "Receita Bruta", "Total Líquido", "Margem %", "Margem Média", "Δ vs. Média",
            "Frete", "Comissão ML", "Imposto", "Custo Produto",
        ]
        display["Receita Bruta"]  = display["Receita Bruta"].map(_brl)
        display["Total Líquido"]  = display["Total Líquido"].map(_brl)
        display["Margem %"]       = display["Margem %"].map(_pct)
        display["Margem Média"]   = display["Margem Média"].map(_pct)
        display["Δ vs. Média"]    = display["Δ vs. Média"].map(lambda v: f"{v*100:+.1f} p.p.")
        for col in ["Frete", "Comissão ML", "Imposto", "Custo Produto"]:
            display[col] = display[col].map(_brl)

        cols_show = [c for c in _COLS_MAIN
                     if show_costs or c["key"] not in ("Frete","Comissão ML","Imposto","Custo Produto")]

        tbl_footer = {
            "produto":       "TOTAL",
            "Receita Bruta": _brl(df_all["receita_total"].sum()),
            "Total Líquido": _brl(df_all["total_liquido"].sum()),
            "Margem %":      _pct(fat_liquido / fat_bruto if fat_bruto else 0),
        }
        data_table(display, cols_show, height=520, footer=tbl_footer)

    st.divider()

    # ── Destaques ──────────────────────────────────────────────────────────────
    c_neg, c_pos = st.columns(2, gap="large")

    with c_neg:
        prej = df_all[df_all["margem"] < 0][
            ["sku", "produto", "receita_total", "total_liquido", "margem"]
        ].sort_values("total_liquido").copy()
        _section_title(
            f"⚠  {len(prej)} SKUs com margem negativa", _RED,
            subtitle="Empresa perde dinheiro em cada venda destes produtos. Veja análise completa na aba Classificação." if not prej.empty else "Nenhum produto com prejuízo neste período.",
        )
        if not prej.empty:
            prej.columns = ["sku", "produto", "Receita Bruta", "Total Líquido", "Margem %"]
            prej["Receita Bruta"]  = prej["Receita Bruta"].map(_brl)
            prej["Total Líquido"]  = prej["Total Líquido"].map(_brl)
            prej["Margem %"]       = prej["Margem %"].map(_pct)
            data_table(prej, _COLS_HIGHLIGHT, height=260)

    with c_pos:
        alta = df_all[df_all["margem"] >= 0.30][
            ["sku", "produto", "receita_total", "total_liquido", "margem"]
        ].sort_values("total_liquido", ascending=False).copy()
        _section_title(
            f"★  {len(alta)} SKUs com margem ≥ 30%", _GREEN,
            subtitle="Produtos mais rentáveis. Priorize estoque e campanhas para estes itens." if not alta.empty else "Nenhum produto com margem acima de 30% neste período.",
        )
        if not alta.empty:
            alta.columns = ["sku", "produto", "Receita Bruta", "Total Líquido", "Margem %"]
            alta["Receita Bruta"]  = alta["Receita Bruta"].map(_brl)
            alta["Total Líquido"]  = alta["Total Líquido"].map(_brl)
            alta["Margem %"]       = alta["Margem %"].map(_pct)
            data_table(alta, _COLS_HIGHLIGHT, height=260)


# ── Utilitários ───────────────────────────────────────────────────────────────
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


def _section_title(texto: str, cor: str, subtitle: str = "") -> None:
    sub = (f"<p style='text-align:center;font-size:0.82rem;color:#525252;margin:0 0 0.5rem'>"
           f"{subtitle}</p>") if subtitle else ""
    st.markdown(
        f"<div style='text-align:center;font-family:Rajdhani,sans-serif;color:{cor};"
        f"font-size:1.05rem;font-weight:700;margin-bottom:0.2rem'>"
        f"{texto}</div>{sub}",
        unsafe_allow_html=True,
    )


_DASHBOARD_COLS_EXCEL = [
    {"key": "status",        "label": "Status",               "fmt": "text",    "width": 14, "total": False},
    {"key": "sku",           "label": "SKU",                  "fmt": "text",    "width": 13},
    {"key": "produto",       "label": "Produto",              "fmt": "text",    "width": 44},
    {"key": "receita_total", "label": "Receita Bruta (R$)",   "fmt": "brl"},
    {"key": "total_liquido", "label": "Total Líquido (R$)",   "fmt": "brl"},
    {"key": "margem",        "label": "Margem %",             "fmt": "pct"},
    {"key": "margem_media",  "label": "Margem Histórica %",   "fmt": "pct",     "total": False},
    {"key": "frete",         "label": "Frete (R$)",           "fmt": "brl"},
    {"key": "comissao_ml",   "label": "Comissão ML (R$)",     "fmt": "brl"},
    {"key": "imposto",       "label": "Imposto (R$)",         "fmt": "brl"},
    {"key": "custo_produto", "label": "Custo Produto (R$)",   "fmt": "brl"},
]


def _to_excel(df) -> bytes:
    return to_excel_styled(df, _DASHBOARD_COLS_EXCEL, sheet_name="Visão Geral")


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
