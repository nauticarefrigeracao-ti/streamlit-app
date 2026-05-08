"""Comparativo MoM — delta KPIs, top movers, tendência, heatmap, tabela completa."""

from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ntc_theme import data_table
from src.analytics.kpis import get_comparativo, get_kpis, get_margem_por_periodo, get_serie_temporal

_NAVY  = "#14283C"
_GREEN = "#1F7A3A"
_RED   = "#B5322B"
_GOLD  = "#BFA168"
_GRAY  = "#9BACBD"


def render(periodo: str, periodos: list[str], filtro_sku: str = "") -> None:
    if len(periodos) < 2:
        st.markdown(
            """
            <div style="background:#F8F9FB;border:1px solid #E4E4E4;border-left:4px solid #BFA168;
                        border-radius:12px;padding:1.25rem 1.5rem;margin-top:1rem;">
              <p style="font-family:'Rajdhani',sans-serif;font-weight:700;font-size:1rem;
                        color:#14283C;margin:0 0 0.4rem;">Comparativo indisponível</p>
              <p style="font-size:0.85rem;color:#525252;margin:0 0 0.75rem;">
                Esta aba compara dois períodos mensais — variação de receita, margem e quais
                produtos cresceram ou caíram.
              </p>
              <p style="font-size:0.82rem;color:#737373;margin:0;">
                <strong>Para habilitar:</strong> importe o relatório de um segundo mês usando
                o painel lateral. Você tem apenas <strong>1 período</strong> carregado até agora.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:60vh;'></div>", unsafe_allow_html=True)
        return

    # ── Seletor período anterior ──────────────────────────────────────────────
    outros = [p for p in periodos if p != periodo]
    col_sel, _ = st.columns([1, 2])
    with col_sel:
        anterior = st.selectbox(
            "Comparar com",
            outros,
            format_func=_fmt_periodo,
            key="comparativo_anterior",
            help="Selecione o período base para comparação",
        )

    df_full = get_comparativo(periodo, anterior)
    df = _filtrar(df_full, filtro_sku)
    n_total = len(df_full)

    if df.empty:
        st.warning(f"Nenhum produto encontrado para '{filtro_sku}'.")
        return

    _nota_filtro(filtro_sku, len(df), n_total)

    kpi_at  = get_kpis(periodo)
    kpi_ant = get_kpis(anterior)

    # ── Delta KPIs ────────────────────────────────────────────────────────────
    st.divider()
    c1, c2, c3, c4 = st.columns(4)

    delta_fat    = kpi_at["fat_bruto"]     - kpi_ant["fat_bruto"]
    delta_liq    = kpi_at["fat_liquido"]   - kpi_ant["fat_liquido"]
    delta_margem = kpi_at["margem_global"] - kpi_ant["margem_global"]
    delta_skus   = kpi_at["total_skus"]    - kpi_ant["total_skus"]

    c1.metric("Faturamento Bruto",  _brl(kpi_at["fat_bruto"]),
              delta=_delta_brl(delta_fat))
    c2.metric("Total Líquido",      _brl(kpi_at["fat_liquido"]),
              delta=_delta_brl(delta_liq))
    c3.metric("Margem Global",      _pct(kpi_at["margem_global"]),
              delta=f"{delta_margem * 100:+.1f} p.p.")
    c4.metric("SKUs",               str(kpi_at["total_skus"]),
              delta=str(delta_skus) if delta_skus else None)

    _comparativo_label(periodo, anterior)
    st.divider()

    # ── Top gainers / losers ──────────────────────────────────────────────────
    col_g, col_l = st.columns(2, gap="large")
    df_com_delta = df.dropna(subset=["delta_receita"])

    with col_g:
        st.subheader("↑ Top 10 Crescimento")
        gainers = df_com_delta.nlargest(10, "delta_receita").copy()
        if gainers.empty:
            st.caption("Sem produtos com crescimento registrado.")
        else:
            fig = px.bar(
                gainers, x="delta_receita", y="produto", orientation="h",
                color_discrete_sequence=[_GREEN],
                labels={"delta_receita": "Δ Receita (R$)", "produto": ""},
                text=gainers["delta_receita"].apply(_brl),
            )
            _apply_bar_layout(fig, height=320)
            st.plotly_chart(fig, use_container_width=True)

    with col_l:
        st.subheader("↓ Top 10 Queda")
        losers = df_com_delta.nsmallest(10, "delta_receita").copy()
        if losers.empty:
            st.caption("Sem produtos com queda registrada.")
        else:
            fig = px.bar(
                losers, x="delta_receita", y="produto", orientation="h",
                color_discrete_sequence=[_RED],
                labels={"delta_receita": "Δ Receita (R$)", "produto": ""},
                text=losers["delta_receita"].apply(_brl),
            )
            _apply_bar_layout(fig, height=320)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Evolução temporal ─────────────────────────────────────────────────────
    st.subheader("Evolução temporal")
    df_serie = get_serie_temporal()
    if len(df_serie) >= 2:
        st.caption("Barras = Faturamento Bruto. Linha = Margem Global (eixo direito).")
        periodos_label = df_serie["data_referencia"].apply(_fmt_periodo)
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=periodos_label,
            y=df_serie["fat_bruto"],
            name="Faturamento Bruto",
            marker_color=_NAVY,
            opacity=0.75,
            yaxis="y1",
            hovertemplate="Faturamento: R$ %{y:,.2f}<extra></extra>",
        ))
        fig_trend.add_trace(go.Scatter(
            x=periodos_label,
            y=df_serie["margem_global"] * 100,
            name="Margem Global (%)",
            mode="lines+markers+text",
            line=dict(color=_GREEN, width=2.5),
            marker=dict(size=7, color=_GREEN),
            yaxis="y2",
            text=df_serie["margem_global"].apply(lambda v: f"{v*100:.1f}%"),
            textposition="top center",
            textfont=dict(size=9, color=_GREEN),
            hovertemplate="Margem Global: %{y:.1f}%<extra></extra>",
        ))
        fig_trend.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_family="Inter, sans-serif", font_color=_NAVY,
            yaxis=dict(title="Faturamento (R$)", tickprefix="R$ ", tickfont_size=9),
            yaxis2=dict(
                title="Margem (%)", overlaying="y", side="right",
                ticksuffix="%", tickfont_size=9, showgrid=False,
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=30, b=10),
            height=300,
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.caption("Importe mais períodos para visualizar a evolução temporal.")

    st.divider()

    # ── Heatmap de margem ─────────────────────────────────────────────────────
    st.subheader("Heatmap de margem — Top SKUs por período")
    df_hm = get_margem_por_periodo(top_n=25)
    if df_hm["data_referencia"].nunique() >= 2:
        st.caption(
            "Margem de cada produto em cada mês. "
            "Vermelho = baixa margem ou prejuízo · Verde = alta margem. "
            "Células em branco = produto não vendido naquele mês."
        )
        pivot = df_hm.pivot_table(
            index="produto", columns="data_referencia", values="margem", aggfunc="first"
        )
        pivot.columns = [_fmt_periodo(c) for c in pivot.columns]
        z_vals = pivot.values * 100
        text_vals = [
            [f"{v:.1f}%" if not pd.isna(v) else "—" for v in row]
            for row in z_vals
        ]
        fig_hm = go.Figure(go.Heatmap(
            z=z_vals,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[
                [0.00, "#7F0000"],
                [0.35, _RED],
                [0.50, "#FFEB99"],
                [0.70, _GREEN],
                [1.00, "#0A4020"],
            ],
            zmin=-20, zmax=50,
            text=text_vals,
            texttemplate="%{text}",
            textfont=dict(size=8),
            hovertemplate="<b>%{y}</b><br>%{x}<br>Margem: %{z:.1f}%<extra></extra>",
            colorbar=dict(title="Margem %", ticksuffix="%", thickness=12),
        ))
        fig_hm.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_family="Inter, sans-serif", font_color=_NAVY,
            yaxis=dict(autorange="reversed", tickfont_size=9),
            xaxis=dict(tickfont_size=10),
            margin=dict(l=0, r=10, t=10, b=10),
            height=max(300, len(pivot) * 22),
        )
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.caption("Importe mais períodos para visualizar o heatmap.")

    st.divider()

    # ── Tabela completa ───────────────────────────────────────────────────────
    st.subheader("Variação por produto")

    busca_col, sort_col, exp_col = st.columns([2, 2, 1])
    with busca_col:
        busca = st.text_input(
            "busca_comp",
            placeholder="🔍  Buscar SKU ou produto...",
            label_visibility="collapsed",
            key="comp_busca_local",
        )
    with sort_col:
        _SORT_OPTS = {
            "Receita Atual ↓":    ("receita_atual",    False),
            "Receita Anterior ↓": ("receita_anterior", False),
            "Δ Receita ↓":        ("delta_receita",    False),
            "Δ Receita ↑":        ("delta_receita",    True),
            "Margem Atual ↓":     ("margem_atual",     False),
            "Margem Atual ↑":     ("margem_atual",     True),
            "Δ Margem ↓":         ("delta_margem",     False),
            "Produto A→Z":        ("produto",          True),
        }
        sort_key = st.selectbox("Ordenar por", list(_SORT_OPTS.keys()),
                                key="comp_sort", label_visibility="collapsed")
    with exp_col:
        st.download_button(
            "📥 Exportar Excel",
            data=_to_excel(df),
            file_name=f"comparativo_{periodo}_vs_{anterior}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    _sort_col, _sort_asc = _SORT_OPTS[sort_key]
    df_show = _filtrar(df, busca).sort_values(_sort_col, ascending=_sort_asc, na_position="last")
    display = df_show[[
        "sku", "produto",
        "receita_atual", "receita_anterior", "delta_receita",
        "margem_atual", "margem_anterior", "delta_margem",
    ]].copy()
    display.columns = [
        "sku", "produto",
        "receita_atual", "receita_ant",
        "delta_receita",
        "margem_atual", "margem_ant",
        "delta_margem",
    ]

    def _fmt_brl_safe(v):
        return _brl(v) if v is not None and str(v) != "nan" else "—"

    def _fmt_pct_safe(v):
        return _pct(v) if v is not None and str(v) != "nan" else "—"

    def _fmt_delta_pp(v):
        try:
            return f"{float(v)*100:+.1f} p.p."
        except Exception:
            return "—"

    display["receita_atual"]  = display["receita_atual"].apply(_fmt_brl_safe)
    display["receita_ant"]    = display["receita_ant"].apply(_fmt_brl_safe)
    display["delta_receita"]  = display["delta_receita"].apply(lambda v: _delta_brl(v) if v is not None and str(v) != "nan" else "—")
    display["margem_atual"]   = display["margem_atual"].apply(_fmt_pct_safe)
    display["margem_ant"]     = display["margem_ant"].apply(_fmt_pct_safe)
    display["delta_margem"]   = display["delta_margem"].apply(_fmt_delta_pp)

    cols_comp = [
        {"key": "sku",          "label": "SKU",                                "type": "mono",  "width": "90px"},
        {"key": "produto",      "label": "Produto"},
        {"key": "receita_atual","label": f"Receita {_fmt_periodo(periodo)}",   "align": "right"},
        {"key": "receita_ant",  "label": f"Receita {_fmt_periodo(anterior)}",  "align": "right"},
        {"key": "delta_receita","label": "Δ Receita",                          "type": "delta", "align": "right"},
        {"key": "margem_atual", "label": f"Margem {_fmt_periodo(periodo)}",    "type": "margem", "align": "right"},
        {"key": "margem_ant",   "label": f"Margem {_fmt_periodo(anterior)}",   "type": "margem", "align": "right"},
        {"key": "delta_margem", "label": "Δ Margem",                           "type": "delta", "align": "right"},
    ]
    data_table(display, cols_comp, height=500)


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


def _comparativo_label(atual: str, anterior: str) -> None:
    st.caption(
        f"Comparando **{_fmt_periodo(atual)}** (período atual) "
        f"com **{_fmt_periodo(anterior)}** (período base)."
    )


def _apply_bar_layout(fig, height: int = 320) -> None:
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font_family="Inter, sans-serif", font_color=_NAVY,
        yaxis={"autorange": "reversed", "tickfont_size": 9},
        margin=dict(l=0, r=10, t=10, b=10),
        showlegend=False,
        height=height,
    )
    fig.update_traces(textposition="outside", textfont_size=9)


def _fmt_periodo(p: str) -> str:
    meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    try:
        y, m, _ = p.split("-")
        return f"{meses[int(m)-1]}/{y}"
    except Exception:
        return p


def _to_excel(df) -> bytes:
    buf = BytesIO()
    with __import__("pandas").ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Comparativo", index=False)
    return buf.getvalue()


def _brl(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def _delta_brl(v: float) -> str:
    try:
        s = f"R$ {abs(float(v)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"+{s}" if v >= 0 else f"-{s}"
    except Exception:
        return "—"


def _pct(v) -> str:
    try:
        return f"{float(v) * 100:.1f}%"
    except Exception:
        return "—"
