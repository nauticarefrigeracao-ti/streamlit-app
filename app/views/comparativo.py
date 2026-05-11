"""Comparativo MoM — delta KPIs, top movers, tendência, heatmap, tabela completa."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ntc_theme import data_table
from src.analytics.kpis import (
    get_comparativo, get_kpis, get_margem_por_periodo,
    get_serie_temporal, get_timeline_produtos,
)
from src.utils.excel_export import to_excel_styled

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

    c1.metric("Faturamento Bruto", _brl(kpi_at["fat_bruto"]),
              delta=_delta_brl(delta_fat),
              help="Receita total do período atual. A seta mostra quanto cresceu ou caiu vs. o período base selecionado.")
    c2.metric("Total Líquido", _brl(kpi_at["fat_liquido"]),
              delta=_delta_brl(delta_liq),
              help="Lucro real do período atual após todos os custos. A seta mostra a variação vs. o período base.")
    c3.metric("Margem Global", _pct(kpi_at["margem_global"]),
              delta=f"{delta_margem * 100:+.1f} p.p.",
              help="% do faturamento que virou lucro no período atual. A variação é em pontos percentuais (p.p.) — ex: −2,7 p.p. significa que a margem caiu 2,7 pontos vs. o período base.")
    c4.metric("SKUs", str(kpi_at["total_skus"]),
              delta=str(delta_skus) if delta_skus else None,
              help="Quantidade de produtos diferentes vendidos no período atual. Variação positiva = mais produtos ativos vs. o período base.")

    _comparativo_label(periodo, anterior)
    st.divider()

    # ── Top gainers / losers ──────────────────────────────────────────────────
    col_g, col_l = st.columns(2, gap="large")
    df_com_delta = df.dropna(subset=["delta_receita"])

    with col_g:
        _titulo(
            "Quem mais cresceu?",
            f"Top 10 por aumento de receita vs. {_fmt_periodo(anterior)} — escala independente do gráfico ao lado",
        )
        gainers = df_com_delta.nlargest(10, "delta_receita").copy()
        if gainers.empty:
            st.caption("Sem produtos com crescimento registrado.")
        else:
            fig = px.bar(
                gainers, x="delta_receita", y="sku", orientation="h",
                color_discrete_sequence=[_GREEN],
                labels={"delta_receita": "Δ Receita (R$)", "sku": ""},
                text=gainers["delta_receita"].apply(_brl),
                custom_data=["produto", "receita_atual", "receita_anterior"],
            )
            fig.update_traces(
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "SKU: %{y}<br>"
                    "Receita atual: R$ %{customdata[1]:,.2f}<br>"
                    "Receita anterior: R$ %{customdata[2]:,.2f}<br>"
                    "Variação: +R$ %{x:,.2f}"
                    "<extra></extra>"
                ),
            )
            _apply_bar_layout(fig, height=320)
            st.plotly_chart(fig, use_container_width=True)

    with col_l:
        _titulo(
            "Quem mais caiu?",
            f"Top 10 por queda de receita vs. {_fmt_periodo(anterior)} — escala independente do gráfico ao lado",
        )
        losers = df_com_delta.nsmallest(10, "delta_receita").copy()
        if losers.empty:
            st.caption("Sem produtos com queda registrada.")
        else:
            fig = px.bar(
                losers, x="delta_receita", y="sku", orientation="h",
                color_discrete_sequence=[_RED],
                labels={"delta_receita": "Δ Receita (R$)", "sku": ""},
                text=losers["delta_receita"].apply(lambda v: _brl(abs(v))),
                custom_data=["produto", "receita_atual", "receita_anterior"],
            )
            fig.update_traces(
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "SKU: %{y}<br>"
                    "Receita atual: R$ %{customdata[1]:,.2f}<br>"
                    "Receita anterior: R$ %{customdata[2]:,.2f}<br>"
                    "Variação: R$ %{x:,.2f}"
                    "<extra></extra>"
                ),
            )
            _apply_bar_layout(fig, height=320)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Evolução temporal ─────────────────────────────────────────────────────
    _titulo(
        "Como o negócio evolui mês a mês?",
        "Faturamento crescendo com margem estável é o cenário ideal — observe se as duas sobem juntas",
    )
    df_serie = get_serie_temporal()
    if len(df_serie) >= 2:
        periodos_label = [
            f"{_fmt_periodo(r['data_referencia'])}<br><span style='font-size:9px;color:#9BACBD'>{int(r['total_skus'])} produtos</span>"
            for _, r in df_serie.iterrows()
        ]
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=periodos_label,
            y=df_serie["fat_bruto"],
            name="Faturamento Bruto",
            marker_color=_NAVY,
            opacity=0.75,
            yaxis="y1",
            customdata=df_serie[["total_skus"]].values,
            hovertemplate="Faturamento: R$ %{y:,.2f}<br>%{customdata[0]:.0f} produtos<extra></extra>",
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
                range=[0, max(df_serie["margem_global"] * 100) * 1.4],
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=50, t=30, b=10),
            height=320,
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.caption("Importe mais períodos para visualizar a evolução temporal.")

    st.divider()

    # ── Heatmap de margem ─────────────────────────────────────────────────────
    _titulo(
        "Esses produtos têm margem ruim todo mês — ou foi só uma vez?",
        "Top produtos por receita · ordenados do pior para o melhor desempenho médio de margem",
    )
    df_hm = get_margem_por_periodo(top_n=40)
    if df_hm["data_referencia"].nunique() >= 2:
        # Apenas produtos presentes em 2+ períodos (mostra tendência, não pontual)
        periodos_por_sku = df_hm.groupby("sku")["data_referencia"].nunique()
        skus_validos = periodos_por_sku[periodos_por_sku >= 2].index
        df_hm = df_hm[df_hm["sku"].isin(skus_validos)]

        # Top 10 por receita total acumulada
        top_skus = (
            df_hm.groupby("sku")["receita_total"].sum()
            .nlargest(10).index
        )
        df_hm = df_hm[df_hm["sku"].isin(top_skus)]

        pivot = df_hm.pivot_table(
            index="sku", columns="data_referencia", values="margem", aggfunc="first"
        )
        pivot.columns = [_fmt_periodo(c) for c in pivot.columns]

        # Ordena pior margem média no topo — problema chama atenção primeiro
        pivot = pivot.loc[pivot.mean(axis=1, skipna=True).sort_values().index]

        # Mapa produto por SKU para o hover
        sku_produto = df_hm.drop_duplicates("sku").set_index("sku")["produto"].to_dict()

        z_vals = pivot.values * 100
        text_vals = [
            [f"{v:.1f}%" if not pd.isna(v) else "—" for v in row]
            for row in z_vals
        ]
        hover_vals = [
            [
                f"<b>{sku_produto.get(sku, sku)}</b><br>SKU: {sku}<br>"
                f"{col}: {'—' if pd.isna(pivot.loc[sku, col]) else f'{pivot.loc[sku, col]*100:.1f}%'}"
                for col in pivot.columns
            ]
            for sku in pivot.index
        ]

        st.markdown(
            """
            <div style="display:flex;gap:1.5rem;justify-content:center;
                        margin:0 0 1rem;flex-wrap:wrap;">
              <span style="font-size:0.82rem;color:#525252;">
                🔴 <b>Vermelho em vários meses</b> = problema estrutural — custo alto ou precificação errada
              </span>
              <span style="font-size:0.82rem;color:#525252;">
                🟢 <b>Verde constante</b> = produto saudável, margem estável
              </span>
              <span style="font-size:0.82rem;color:#525252;">
                <b>—</b> = não vendido naquele mês
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        fig_hm = go.Figure(go.Heatmap(
            z=z_vals,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            customdata=hover_vals,
            colorscale=[
                [0.00, "#7F0000"],
                [0.30, _RED],
                [0.50, "#FFEB99"],
                [0.65, _GREEN],
                [1.00, "#0A4020"],
            ],
            zmin=-15, zmax=45,
            text=text_vals,
            texttemplate="%{text}",
            textfont=dict(size=10, color="white"),
            hovertemplate="%{customdata}<extra></extra>",
            colorbar=dict(
                title=dict(text="Margem", side="right"),
                ticksuffix="%", thickness=12,
                tickfont_size=9,
            ),
        ))
        fig_hm.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_family="Inter, sans-serif", font_color=_NAVY,
            yaxis=dict(autorange="reversed", tickfont_size=10),
            xaxis=dict(tickfont_size=11, side="bottom"),
            margin=dict(l=10, r=10, t=10, b=10),
            height=max(280, len(pivot) * 38),
        )
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.caption("Importe mais períodos para visualizar o heatmap.")

    st.divider()

    # ── Tabela completa ───────────────────────────────────────────────────────
    _titulo(
        "Produto a produto — o que mudou?",
        "Compare receita e margem de cada SKU entre os dois períodos selecionados",
    )

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
            "Δ Receita ↓":        ("delta_receita",    False),
            "Δ Receita ↑":        ("delta_receita",    True),
            "Receita Atual ↓":    ("receita_atual",    False),
            "Receita Anterior ↓": ("receita_anterior", False),
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
            data=_to_excel(df, periodo, anterior),
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
        {"key": "sku",          "label": "SKU",                                "type": "mono",  "width": "90px",
         "help": "Código de identificação único do produto"},
        {"key": "produto",      "label": "Produto",
         "help": "Nome completo do produto"},
        {"key": "receita_atual","label": f"Receita {_fmt_periodo(periodo)}",   "align": "right",
         "help": f"Faturamento bruto do produto no período atual ({_fmt_periodo(periodo)})"},
        {"key": "receita_ant",  "label": f"Receita {_fmt_periodo(anterior)}",  "align": "right",
         "help": f"Faturamento bruto do produto no período base ({_fmt_periodo(anterior)})"},
        {"key": "delta_receita","label": "Δ Receita",                          "type": "delta", "align": "right",
         "help": "Variação de receita entre os dois períodos. Verde = cresceu · Vermelho = caiu"},
        {"key": "margem_atual", "label": f"Margem {_fmt_periodo(periodo)}",    "type": "margem", "align": "right",
         "help": f"% de margem do produto no período atual ({_fmt_periodo(periodo)})"},
        {"key": "margem_ant",   "label": f"Margem {_fmt_periodo(anterior)}",   "type": "margem", "align": "right",
         "help": f"% de margem do produto no período base ({_fmt_periodo(anterior)})"},
        {"key": "delta_margem", "label": "Δ Margem",                           "type": "delta", "align": "right",
         "help": "Variação de margem entre os períodos em pontos percentuais (p.p.). Ex: +2 p.p. = margem subiu 2 pontos"},
    ]
    data_table(display, cols_comp, height=500)

    # ── Tabela evolutiva (todos os meses) ─────────────────────────────────────
    _render_timeline(filtro_sku)


# ── Utilitários ───────────────────────────────────────────────────────────────
def _titulo(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"<div style='text-align:center;font-family:\"Source Sans Pro\",sans-serif;"
        f"font-weight:600;font-size:1.45rem;color:#14283C;line-height:1.3;"
        f"margin:0 0 0.2rem'>{title}</div>",
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(
            f"<div style='text-align:center;font-size:0.85rem;color:#525252;"
            f"margin:0 0 0.8rem'>{subtitle}</div>",
            unsafe_allow_html=True,
        )


def _render_timeline(filtro_sku: str = "") -> None:
    st.divider()

    with st.expander("📅  Tabela evolutiva — todos os meses", expanded=False):
        st.markdown(
            "<p style='font-size:0.82rem;color:#525252;margin:0 0 0.75rem'>"
            "Veja a trajetória de cada produto em todos os meses carregados no sistema. "
            "Escolha a métrica, busque um produto e exporte o histórico completo."
            "</p>",
            unsafe_allow_html=True,
        )

        df_tl = get_timeline_produtos()
        if df_tl.empty:
            st.caption("Sem dados disponíveis.")
            return

        # ── Controles ─────────────────────────────────────────────────────────
        metrica = st.radio(
            "Métrica da timeline",
            ["Receita Bruta", "Total Líquido", "Margem %"],
            horizontal=True,
            key="tl_metrica",
        )

        c_busca, c_sort, c_exp = st.columns([3, 2, 1])
        with c_busca:
            busca_tl = st.text_input(
                "busca_tl",
                placeholder="🔍  Buscar SKU ou produto...",
                label_visibility="collapsed",
                key="tl_busca",
            )
        with c_sort:
            _SORT_TL = {
                "Receita Total ↓":    ("receita_sum", False),
                "Produto A→Z":        ("produto",     True),
                "Mais meses ativo ↓": ("n_meses",     False),
            }
            sort_tl = st.selectbox(
                "Ordenar por", list(_SORT_TL.keys()),
                key="tl_sort", label_visibility="collapsed",
            )

        # ── Dados ─────────────────────────────────────────────────────────────
        df_tl = _filtrar(df_tl, filtro_sku)
        df_tl = _filtrar(df_tl, busca_tl)

        val_col  = {"Receita Bruta": "receita_total", "Total Líquido": "total_liquido", "Margem %": "margem"}[metrica]
        fmt_fn   = _pct if metrica == "Margem %" else _brl
        col_type = "margem" if metrica == "Margem %" else "text"

        # Ordenação por metadados
        meta = (
            df_tl.groupby("sku")
            .agg(receita_sum=("receita_total", "sum"),
                 n_meses=("data_referencia", "nunique"),
                 produto=("produto", "first"))
            .reset_index()
        )
        sort_col_name, sort_asc = _SORT_TL[sort_tl]
        meta = meta.sort_values(sort_col_name, ascending=sort_asc)

        # Pivot SKU × período
        pivot = df_tl.pivot_table(
            index=["sku", "produto"],
            columns="data_referencia",
            values=val_col,
            aggfunc="first",
        ).reset_index()
        pivot.columns.name = None

        sku_order = {sku: i for i, sku in enumerate(meta["sku"])}
        pivot["_order"] = pivot["sku"].map(sku_order).fillna(9999)
        pivot = pivot.sort_values("_order").drop(columns="_order")

        period_cols = sorted([c for c in pivot.columns if c not in ["sku", "produto"]])

        # Coluna de resumo (Total ou Média)
        if metrica == "Margem %":
            pivot["_resumo"] = pivot[period_cols].mean(axis=1, skipna=True)
            resumo_label = "Média"
            resumo_fmt   = _pct
            resumo_type  = "margem"
        else:
            pivot["_resumo"] = pivot[period_cols].sum(axis=1, skipna=True)
            resumo_label = "Total"
            resumo_fmt   = _brl
            resumo_type  = "text"

        # Display formatado
        display = pivot[["sku", "produto"]].copy()
        key_map: dict[str, str] = {}
        for p in period_cols:
            safe = f"m_{p.replace('-', '_')}"
            key_map[p] = safe
            display[safe] = pivot[p].apply(lambda v: fmt_fn(v) if pd.notna(v) else "—")
        display["_resumo"] = pivot["_resumo"].apply(resumo_fmt)

        # Excel com valores brutos
        raw_export = pivot[["sku", "produto"] + period_cols + ["_resumo"]].copy()
        raw_export.columns = (
            ["SKU", "Produto"]
            + [_fmt_periodo(p) for p in period_cols]
            + [resumo_label]
        )
        with c_exp:
            st.download_button(
                "📥 Excel",
                data=_to_excel_timeline(raw_export, [_fmt_periodo(p) for p in period_cols], metrica),
                file_name=f"timeline_{metrica.lower().replace(' ', '_').replace('%', 'pct')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        # Definição dinâmica de colunas
        cols_tl = [
            {"key": "sku",     "label": "SKU",     "type": "mono", "width": "90px",
             "help": "Código único do produto"},
            {"key": "produto", "label": "Produto",
             "help": "Nome do produto"},
        ]
        for p in period_cols:
            cols_tl.append({
                "key":   key_map[p],
                "label": _fmt_periodo(p),
                "type":  col_type,
                "align": "right",
            })
        cols_tl.append({
            "key":   "_resumo",
            "label": resumo_label,
            "type":  resumo_type,
            "align": "right",
            "help":  "Média de margem nos meses ativos" if metrica == "Margem %" else "Soma de todos os meses",
        })

        n = len(display)
        st.caption(f"{n} produto{'s' if n != 1 else ''} · {len(period_cols)} período{'s' if len(period_cols) != 1 else ''}")
        data_table(display, cols_tl, height=560)


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
        margin=dict(l=0, r=100, t=10, b=10),
        showlegend=False,
        height=height,
    )
    fig.update_traces(textposition="outside", textfont_size=9, cliponaxis=False)


def _fmt_periodo(p: str) -> str:
    meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    try:
        y, m, _ = p.split("-")
        return f"{meses[int(m)-1]}/{y}"
    except Exception:
        return p


def _to_excel(df, periodo: str = "", anterior: str = "") -> bytes:
    cols = [
        {"key": "sku",              "label": "SKU",                    "fmt": "text",      "width": 13},
        {"key": "produto",          "label": "Produto",                "fmt": "text",      "width": 42},
        {"key": "receita_atual",    "label": f"Receita {_fmt_periodo(periodo) if periodo else 'Atual'} (R$)",    "fmt": "brl"},
        {"key": "receita_anterior", "label": f"Receita {_fmt_periodo(anterior) if anterior else 'Anterior'} (R$)", "fmt": "brl"},
        {"key": "delta_receita",    "label": "Δ Receita (R$)",         "fmt": "delta_brl"},
        {"key": "margem_atual",     "label": f"Margem {_fmt_periodo(periodo) if periodo else 'Atual'}",    "fmt": "pct"},
        {"key": "margem_anterior",  "label": f"Margem {_fmt_periodo(anterior) if anterior else 'Anterior'}", "fmt": "pct"},
        {"key": "delta_margem",     "label": "Δ Margem (p.p.)",        "fmt": "delta_pp",  "total": False},
    ]
    return to_excel_styled(df, cols, sheet_name="Comparativo")


def _to_excel_timeline(df: "pd.DataFrame", period_cols: list[str], metrica: str) -> bytes:
    fmt = "pct" if metrica == "Margem %" else "brl"
    resumo_label = "Média" if metrica == "Margem %" else "Total"
    cols = [
        {"key": "SKU",     "label": "SKU",     "fmt": "text", "width": 13},
        {"key": "Produto", "label": "Produto", "fmt": "text", "width": 42},
    ]
    for p in period_cols:
        cols.append({"key": p, "label": p, "fmt": fmt, "total": False})
    cols.append({"key": resumo_label, "label": resumo_label, "fmt": fmt, "total": False})
    return to_excel_styled(df, cols, sheet_name="Timeline", show_totals=False, freeze_cols=2)


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
