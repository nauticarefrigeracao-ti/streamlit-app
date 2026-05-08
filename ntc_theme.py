"""
Grupo Náutica Refrigeração — Theme Helper para Streamlit
=========================================================

Módulo único que centraliza:
  • Constantes de cores e tipografia (mesmos valores dos tokens do design system).
  • A função `apply_theme()`, que injeta CSS no app para forçar a identidade
    visual da marca (botões, headers, métricas, sidebar, etc.).
  • Helpers para produzir componentes consistentes:
      - `brand_header(titulo, subtitulo)` — topbar com nome + linha dourada
      - `metric_card(label, valor, delta=None)` — card de métrica estilizado
      - `badge(texto, tipo)` — badge inline (navy/gold/success/warning/danger/info)
      - `kpi_row(items)` — linha de KPIs uniforme

Uso típico
----------
    import streamlit as st
    from ntc_theme import apply_theme, brand_header, metric_card, badge

    st.set_page_config(page_title="Sistema NTC", layout="wide")
    apply_theme()

    brand_header("Painel de Vendas", "Grupo Náutica Refrigeração")
    metric_card("Vendas hoje", "R$ 12.450", "+8,2%")
    st.markdown(badge("Ativo", "success"), unsafe_allow_html=True)
"""

from __future__ import annotations

import streamlit as st

# --------------------------------------------------------------------------- #
# Tokens (espelho dos arquivos tokens.json / tokens.css)                       #
# --------------------------------------------------------------------------- #

class Color:
    """Paleta da marca. Sempre referencie aqui em vez de hardcodear hex."""
    NAVY = "#14283C"
    NAVY_600 = "#1E3550"
    NAVY_500 = "#2E4A66"
    NAVY_50 = "#E7EBF0"

    GOLD = "#BFA168"
    GOLD_600 = "#A8884F"
    GOLD_100 = "#F0E6CE"

    BG = "#F1F1F1"
    SURFACE = "#FFFFFF"
    BORDER = "#E4E4E4"
    TEXT_MUTED = "#525252"

    SUCCESS = "#1F7A3A"
    WARNING = "#C8901C"
    DANGER = "#B5322B"
    INFO = "#2E6FA8"


class Font:
    PRIMARY = "'Inter', 'Segoe UI', system-ui, sans-serif"
    DISPLAY = "'Rajdhani', 'Inter', sans-serif"


# --------------------------------------------------------------------------- #
# CSS injection                                                                #
# --------------------------------------------------------------------------- #

_CSS = f"""
<style>
/* -------- Web fonts (carrega Inter + Rajdhani do Google Fonts) ----------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Rajdhani:wght@500;600;700&display=swap');

/* -------- Variáveis CSS (mesmos tokens) ---------------------------------- */
:root {{
  --ntc-navy: {Color.NAVY};
  --ntc-navy-600: {Color.NAVY_600};
  --ntc-gold: {Color.GOLD};
  --ntc-gold-600: {Color.GOLD_600};
  --ntc-bg: {Color.BG};
  --ntc-surface: {Color.SURFACE};
  --ntc-border: {Color.BORDER};
}}

/* -------- Base ----------------------------------------------------------- */
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--ntc-bg);
  font-family: {Font.PRIMARY};
  color: {Color.NAVY};
}}

/* Cabeçalho/topbar do Streamlit */
[data-testid="stHeader"] {{
  background: transparent;
  border-bottom: 1px solid var(--ntc-border);
}}

/* Headings -> tipografia display */
h1, h2, h3 {{
  font-family: {Font.DISPLAY};
  letter-spacing: 0.02em;
  color: {Color.NAVY};
}}
h1 {{ font-weight: 700; }}
h2 {{ font-weight: 600; }}
h3 {{ font-weight: 600; }}

/* -------- Sidebar -------------------------------------------------------- */
[data-testid="stSidebar"] {{
  background: {Color.NAVY};
}}
[data-testid="stSidebar"] * {{
  color: #ffffff !important;
}}
[data-testid="stSidebar"] hr {{
  border-color: rgba(255,255,255,0.15);
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a {{
  color: {Color.GOLD} !important;
  font-weight: 600;
}}

/* -------- Botões --------------------------------------------------------- */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {{
  background: {Color.NAVY};
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 0.6rem 1.25rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 0.85rem;
  transition: background 200ms ease, box-shadow 200ms ease;
}}
.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {{
  background: {Color.NAVY_600};
}}
.stButton > button:focus {{
  box-shadow: 0 0 0 3px rgba(191,161,104,0.45);
  outline: none;
}}
/* Ação primária — sempre dourado (respeita primaryColor do config.toml) */
button[data-testid="stBaseButton-primary"] {{
  background: {Color.GOLD} !important;
  color: {Color.NAVY} !important;
}}
button[data-testid="stBaseButton-primary"]:hover {{
  background: {Color.GOLD_600} !important;
  color: #ffffff !important;
}}
button[data-testid="stBaseButton-primary"]:disabled {{
  background: {Color.GOLD} !important;
  color: {Color.NAVY} !important;
  opacity: 0.42 !important;
  cursor: not-allowed !important;
}}

/* -------- Inputs --------------------------------------------------------- */
[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input {{
  border-radius: 8px !important;
  border: 1px solid {Color.BORDER} !important;
  background: {Color.SURFACE} !important;
}}
[data-baseweb="input"] > div:focus-within,
[data-baseweb="select"] > div:focus-within {{
  border-color: {Color.GOLD} !important;
  box-shadow: 0 0 0 3px rgba(191,161,104,0.35) !important;
}}

/* -------- Métricas ------------------------------------------------------- */
[data-testid="stMetric"] {{
  background: {Color.SURFACE};
  border: 1px solid {Color.BORDER};
  border-left: 4px solid {Color.GOLD};
  border-radius: 12px;
  padding: 1rem 1.25rem;
  box-shadow: 0 1px 3px rgba(20,40,60,0.06);
}}
[data-testid="stMetricLabel"] {{
  color: {Color.TEXT_MUTED};
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 500;
}}
[data-testid="stMetricValue"] {{
  color: {Color.NAVY};
  font-family: {Font.DISPLAY};
  font-weight: 700;
}}

/* -------- Tabelas / DataFrames ------------------------------------------ */
[data-testid="stDataFrame"] {{
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid {Color.BORDER};
}}

/* -------- Tabs ----------------------------------------------------------- */
.stTabs [data-baseweb="tab-list"] {{
  gap: 0.25rem;
  border-bottom: 1px solid {Color.BORDER};
}}
.stTabs [data-baseweb="tab"] {{
  color: {Color.TEXT_MUTED};
  font-weight: 500;
  font-size: 0.9rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}}
.stTabs [aria-selected="true"] {{
  color: {Color.NAVY} !important;
  border-bottom: 2px solid {Color.GOLD} !important;
}}

/* -------- Componentes customizados (helpers abaixo) ---------------------- */
.ntc-brand-header {{
  background: {Color.NAVY};
  color: #ffffff;
  padding: 1.5rem 1.75rem;
  border-radius: 12px;
  border-bottom: 4px solid {Color.GOLD};
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 8px rgba(20,40,60,0.10);
}}
.ntc-brand-header h1 {{
  font-family: {Font.DISPLAY};
  font-weight: 700;
  font-size: 1.75rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin: 0;
  color: #ffffff;
}}
.ntc-brand-header p {{
  margin: 0.25rem 0 0;
  color: {Color.GOLD};
  font-size: 0.9rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 500;
}}

.ntc-card-metric {{
  background: {Color.SURFACE};
  border: 1px solid {Color.BORDER};
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  box-shadow: 0 1px 3px rgba(20,40,60,0.06);
}}
.ntc-card-metric .ntc-label {{
  color: {Color.TEXT_MUTED};
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 500;
  margin: 0 0 0.5rem;
}}
.ntc-card-metric .ntc-value {{
  color: {Color.NAVY};
  font-family: {Font.DISPLAY};
  font-weight: 700;
  font-size: 1.75rem;
  margin: 0;
}}
.ntc-card-metric .ntc-delta-up   {{ color: {Color.SUCCESS}; font-size: 0.85rem; font-weight: 600; }}
.ntc-card-metric .ntc-delta-down {{ color: {Color.DANGER};  font-size: 0.85rem; font-weight: 600; }}

.ntc-badge {{
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 9999px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}}
.ntc-badge.navy    {{ background: {Color.NAVY_50};  color: {Color.NAVY};   }}
.ntc-badge.gold    {{ background: {Color.GOLD_100}; color: #65522F;        }}
.ntc-badge.success {{ background: rgba(31,122,58,0.12);  color: {Color.SUCCESS}; }}
.ntc-badge.warning {{ background: rgba(200,144,28,0.15); color: #65522F;        }}
.ntc-badge.danger  {{ background: rgba(181,50,43,0.12);  color: {Color.DANGER};  }}
.ntc-badge.info    {{ background: rgba(46,111,168,0.12); color: {Color.INFO};    }}

/* -------- HTML Data Table (data_table helper) --------------------------- */
.ntc-table-wrap {{
  border-radius: 12px;
  border: 1px solid {Color.BORDER};
  box-shadow: 0 1px 4px rgba(20,40,60,0.08);
  background: {Color.SURFACE};
  overflow: auto;
}}
.ntc-tbl {{
  width: 100%;
  border-collapse: collapse;
  font-family: {Font.PRIMARY};
}}
.ntc-tbl thead {{ position: sticky; top: 0; z-index: 2; }}
.ntc-tbl th {{
  background: #F8F9FB;
  padding: 10px 14px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: {Color.TEXT_MUTED};
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border-bottom: 1px solid {Color.BORDER};
  white-space: nowrap;
}}
.ntc-tbl td {{
  padding: 11px 14px;
  font-size: 13px;
  color: {Color.NAVY};
  border-bottom: 1px solid #F1F1F1;
  vertical-align: middle;
}}
.ntc-tbl tbody tr:last-child td {{ border-bottom: none; }}
.ntc-tbl tbody tr:hover td {{ background: rgba(20,40,60,0.03); }}
.ntc-tbl-mono {{
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
  font-weight: 500;
  color: {Color.NAVY};
}}
.ntc-tbl-muted {{ color: {Color.TEXT_MUTED}; font-size: 12px; }}
.ntc-tbl-pill {{
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  white-space: nowrap;
}}
.ntc-tbl-delta-pos {{ color: {Color.SUCCESS}; font-weight: 600; font-size: 12px; }}
.ntc-tbl-delta-neg {{ color: {Color.DANGER};  font-weight: 600; font-size: 12px; }}
.ntc-tbl-margem-red   {{ color: #B5322B; font-weight: 600; font-size: 12px; }}
.ntc-tbl-margem-blue  {{ color: #2E6FA8; font-weight: 600; font-size: 12px; }}
.ntc-tbl-margem-green {{ color: #1F7A3A; font-weight: 600; font-size: 12px; }}

</style>
"""


# --------------------------------------------------------------------------- #
# API pública                                                                 #
# --------------------------------------------------------------------------- #

def apply_theme() -> None:
    """Injeta o CSS da marca. Chame uma vez por página, logo após `set_page_config`."""
    st.markdown(_CSS, unsafe_allow_html=True)


def brand_header(titulo: str, subtitulo: str | None = None) -> None:
    """Renderiza o cabeçalho navy + linha dourada com o nome do sistema/seção."""
    sub = f"<p>{subtitulo}</p>" if subtitulo else ""
    st.markdown(
        f"""
        <div class="ntc-brand-header">
          <h1>{titulo}</h1>
          {sub}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, valor: str, delta: str | None = None,
                delta_positive: bool = True) -> None:
    """Card de métrica estilizado, alternativa visual ao st.metric."""
    delta_html = ""
    if delta is not None:
        cls = "ntc-delta-up" if delta_positive else "ntc-delta-down"
        arrow = "▲" if delta_positive else "▼"
        delta_html = f'<div class="{cls}">{arrow} {delta}</div>'
    st.markdown(
        f"""
        <div class="ntc-card-metric">
          <p class="ntc-label">{label}</p>
          <p class="ntc-value">{valor}</p>
          {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(texto: str, tipo: str = "navy") -> str:
    """
    Retorna o HTML de uma badge inline.
    Uso: st.markdown(badge("Ativo", "success"), unsafe_allow_html=True)
    Tipos válidos: navy, gold, success, warning, danger, info
    """
    tipos_validos = {"navy", "gold", "success", "warning", "danger", "info"}
    if tipo not in tipos_validos:
        tipo = "navy"
    return f'<span class="ntc-badge {tipo}">{texto}</span>'


def data_table(df, columns: list[dict], height: int = 480, footer: dict | None = None) -> None:
    """
    Renderiza DataFrame como tabela HTML estilizada (padrão NTC/devoluções).

    columns: lista de dicts:
      key    — nome da coluna no DataFrame
      label  — cabeçalho exibido
      type   — "text" | "mono" | "badge" | "delta"  (padrão: "text")
      align  — "left" | "right" | "center"           (padrão: "left")
      colors — {valor: (bg, fg)}  somente para type="badge"
      width  — string CSS opcional, ex.: "90px"
    """
    import html as _h
    import math

    ths = ""
    for col in columns:
        align = col.get("align", "left")
        w = f"width:{col['width']};" if col.get("width") else ""
        tip = col.get("help", "")
        if tip:
            title_attr = f' title="{_h.escape(tip)}"'
            cursor_style = "cursor:help;"
            icon = (' <span style="color:#9BACBD;font-size:9px;'
                    'vertical-align:middle;font-weight:400;">ⓘ</span>')
        else:
            title_attr = ""
            cursor_style = ""
            icon = ""
        label_html = _h.escape(col["label"]) + icon
        ths += (f'<th style="text-align:{align};{w}{cursor_style}"'
                f'{title_attr}>{label_html}</th>')

    trs = ""
    for _, row in df.iterrows():
        tds = ""
        for col in columns:
            val = row.get(col["key"], None)
            ctype = col.get("type", "text")
            align = col.get("align", "left")
            a = f"text-align:{align};"

            if val is None or (isinstance(val, float) and math.isnan(val)):
                s = "—"
            else:
                s = str(val)

            if ctype == "badge":
                bg, fg = col.get("colors", {}).get(s, ("#E7EBF0", "#14283C"))
                tip = col.get("tooltips", {}).get(s, "")
                title_attr = f' title="{_h.escape(tip)}"' if tip else ""
                tds += (f'<td style="{a}"><span class="ntc-tbl-pill" '
                        f'style="background:{bg};color:{fg};cursor:help;"{title_attr}>'
                        f'{_h.escape(s)}</span></td>')
            elif ctype == "mono":
                tds += f'<td style="{a}"><span class="ntc-tbl-mono">{_h.escape(s)}</span></td>'
            elif ctype == "delta":
                stripped = s.lstrip()
                dcls = ("ntc-tbl-delta-neg" if stripped.startswith("-") else
                        "ntc-tbl-muted"      if s in ("—", "", "0")      else
                        "ntc-tbl-delta-pos")
                tds += f'<td style="{a}"><span class="{dcls}">{_h.escape(s)}</span></td>'
            elif ctype == "margem":
                try:
                    pct_val = float(s.replace("%", "").replace(",", ".").strip())
                    mcls = ("ntc-tbl-margem-red"   if pct_val < 5.0  else
                            "ntc-tbl-margem-blue"  if pct_val < 15.0 else
                            "ntc-tbl-margem-green")
                except Exception:
                    mcls = ""
                tds += f'<td style="{a}"><span class="{mcls}">{_h.escape(s)}</span></td>'
            else:
                tds += f'<td style="{a}">{_h.escape(s)}</td>'

        trs += f"<tr>{tds}</tr>"

    footer_html = ""
    if footer:
        ftds = ""
        for col in columns:
            val = footer.get(col["key"], "")
            align = col.get("align", "left")
            a = f"text-align:{align};"
            s = str(val) if val not in (None, "") else ""
            ftds += (f'<td style="{a}font-weight:600;color:#14283C;'
                     f'font-size:12px;border-top:2px solid #E4E4E4;">{_h.escape(s)}</td>')
        footer_html = f"<tfoot><tr>{ftds}</tr></tfoot>"

    st.markdown(
        f'<div class="ntc-table-wrap" style="max-height:{height}px;">'
        f'<table class="ntc-tbl">'
        f'<thead><tr>{ths}</tr></thead>'
        f'<tbody>{trs}</tbody>'
        f'{footer_html}'
        f'</table></div>',
        unsafe_allow_html=True,
    )


def kpi_row(items: list[dict]) -> None:
    """
    Renderiza uma linha de KPIs uniforme.
    items: lista de dicts {"label": str, "valor": str, "delta": str|None, "up": bool}
    """
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            metric_card(
                item["label"],
                item["valor"],
                item.get("delta"),
                item.get("up", True),
            )
