import base64
import logging
import os
import sys
import threading
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.backup import backup_to_github, restore_from_github
from src.db.schema import init_db
from src.analytics.kpis import get_periodos
from src.etl.pipeline import run as run_pipeline
from ntc_theme import apply_theme

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# ── Page config ──────────────────────────────────────────────────────────────
_icon_path = Path("assets") / "simbolo.png"
_page_icon = str(_icon_path) if _icon_path.exists() else "📊"
st.set_page_config(
    page_title="Grupo Náutica Refrigeração",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

st.markdown("""
<style>
/* ── Layout resets ─────────────────────────────────────────────────────────── */
.block-container, .stApp .block-container {
    padding: 10px 1.4rem 1rem !important;
    max-width: 100% !important;
    margin: 0 !important;
}
section[data-testid="stMain"],
div[data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

/* ── Sidebar: estrutura ──────────────────────────────────────────────────── */
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div > div,
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
[data-testid="stSidebarHeader"] {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    min-height: 0 !important;
}
[data-testid="stSidebarUserContent"] { margin-top: -20px !important; }
[data-testid="stSidebar"] .stVerticalBlock   { gap: 0.55rem !important; }
[data-testid="stSidebar"] .stElementContainer { margin-bottom: 0 !important; }

/* ── Sidebar: labels (nativas Streamlit) ─────────────────────────────────── */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    color: rgba(255,255,255,0.65) !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    line-height: 1.2 !important;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
    margin-top: 0.3rem !important;
    margin-bottom: 0.15rem !important;
}
/* Força markdown <p> (título Filtros etc.) a ser branco */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #ffffff !important;
    font-family: 'Rajdhani', 'Inter', sans-serif !important;
}

/* ── Sidebar: selectbox — fundo branco, texto escuro ────────────────────── */
[data-testid="stSidebar"] [data-baseweb="select"],
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
    border-color: #BFA168 !important;
    box-shadow: 0 0 0 2px rgba(191,161,104,0.35) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] div[class*="singleValue"],
[data-testid="stSidebar"] [data-baseweb="select"] input {
    color: #14283C !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg { fill: #525252 !important; }

/* ── Sidebar: text inputs — fundo branco, texto escuro ──────────────────── */
[data-testid="stSidebar"] [data-baseweb="input"],
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] .stTextInput > div > div {
    background: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-baseweb="input"]:focus-within,
[data-testid="stSidebar"] [data-baseweb="input"] > div:focus-within {
    border-color: #BFA168 !important;
    box-shadow: 0 0 0 2px rgba(191,161,104,0.35) !important;
}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] [data-baseweb="input"] input {
    color: #14283C !important;
    background: transparent !important;
    caret-color: #BFA168 !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder,
[data-testid="stSidebar"] [data-baseweb="input"] input::placeholder {
    color: #8C9BAD !important;
}

/* ── Sidebar: file uploader ──────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background: rgba(255,255,255,0.07) !important;
    border: 1.5px dashed rgba(191,161,104,0.55) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] small {
    color: rgba(255,255,255,0.70) !important;
}

/* ── Sidebar: Browse files button ────────────────────────────────────────── */
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    background: rgba(255,255,255,0.10) !important;
    border: 1px solid rgba(255,255,255,0.22) !important;
    color: #ffffff !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {
    border-color: #BFA168 !important;
    background: rgba(191,161,104,0.18) !important;
}

/* ── Sidebar: PROCESSAR button ───────────────────────────────────────────── */
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"],
[data-testid="stSidebar"] .stButton > button {
    background-color: #BFA168 !important;
    background:       #BFA168 !important;
    color:            #14283C !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    border: none !important;
    border-radius: 8px !important;
    opacity: 1 !important;
    transition: background 0.2s, opacity 0.2s !important;
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover,
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #A8884F !important;
    background:       #A8884F !important;
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:disabled,
[data-testid="stSidebar"] .stButton > button:disabled {
    background-color: #BFA168 !important;
    background:       #BFA168 !important;
    color:            #14283C !important;
    opacity: 0.42 !important;
    cursor: not-allowed !important;
}

/* ── Topbar Streamlit ─────────────────────────────────────────────────────── */
header[data-testid="stHeader"] {
    background: transparent !important;
    border-bottom: none !important;
    box-shadow: none !important;
}

/* ── st.metric cards ─────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #E4E4E4 !important;
    border-left: 4px solid #BFA168 !important;
    border-radius: 12px !important;
    padding: 1rem 1.25rem !important;
    box-shadow: 0 1px 3px rgba(20,40,60,0.06) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    color: #525252 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Rajdhani', 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.65rem !important;
    color: #14283C !important;
}

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.25rem;
    border-bottom: 2px solid #E4E4E4;
    margin-bottom: 1.5rem;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #737373;
    padding: 0.6rem 1.1rem;
    border-radius: 4px 4px 0 0;
}
.stTabs [aria-selected="true"] {
    color: #14283C !important;
    border-bottom: 3px solid #BFA168 !important;
    font-weight: 700 !important;
}

/* ── Section headers ──────────────────────────────────────────────────────── */
h2, h3 { text-align: left !important; }

/* ── DataFrames ───────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #E4E4E4;
}

/* ── Download / action buttons ────────────────────────────────────────────── */
[data-testid="column"] .stDownloadButton > button,
[data-testid="column"] .stButton > button {
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)


# ── Startup ──────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _startup() -> None:
    restore_from_github()
    init_db()


_startup()


# ── Helpers ──────────────────────────────────────────────────────────────────
def _logo_b64() -> tuple[str | None, str | None]:
    candidates = [
        ("simbolo.svg",       "svg+xml"),
        ("simbolo.png",       "png"),
        ("logo-compacto.png", "png"),
        ("logo-circular.jpg", "jpeg"),
    ]
    for nome, mime in candidates:
        p = Path("assets") / nome
        if p.exists() and p.stat().st_size > 100:
            return base64.b64encode(p.read_bytes()).decode("ascii"), mime
    return None, None


def _render_header() -> None:
    b64, mime = _logo_b64()
    logo_tag = (
        f"<img src='data:image/{mime};base64,{b64}' "
        f"style='width:76px;height:auto;display:block;flex-shrink:0;' alt='NTC'>"
        if b64 else ""
    )
    st.markdown(
        f"<div style='background:#14283C;border-radius:12px;border-bottom:4px solid #BFA168;"
        f"padding:1.25rem 1.75rem;margin-bottom:1.25rem;"
        f"box-shadow:0 4px 8px rgba(20,40,60,0.10);display:flex;align-items:center;gap:1.25rem;'>"
        f"{logo_tag}"
        f"<div>"
        f"<div style='font-family:Rajdhani,Inter,\"Segoe UI\",sans-serif;font-size:1.75rem;"
        f"font-weight:700;color:#fff;letter-spacing:0.04em;"
        f"text-transform:uppercase;line-height:1.1;margin:0;'>"
        f"Análise de Margem e Faturamento</div>"
        f"<div style='color:#BFA168;font-size:0.8rem;font-weight:500;"
        f"letter-spacing:0.06em;text-transform:uppercase;margin-top:4px;'>"
        f"Grupo Náutica Refrigeração</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


def _fmt_periodo(p: str) -> str:
    meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    try:
        y, m, _ = p.split("-")
        return f"{meses[int(m)-1]}/{y}"
    except Exception:
        return p


def _section_label(texto: str) -> None:
    st.markdown(
        f"<p style='color:rgba(255,255,255,0.65);font-size:0.68rem;font-weight:600;"
        f"letter-spacing:0.10em;text-transform:uppercase;margin:0.6rem 0 0.15rem'>"
        f"{texto}</p>",
        unsafe_allow_html=True,
    )


def _sidebar_import() -> None:
    uploaded = st.file_uploader(
        "Importar Relatório",
        type=["csv", "xlsx", "xls"],
        label_visibility="visible",
        key="upload_relatorio",
        help="Relatório mensal exportado do Mercado Livre / Tiny / Olist. Colunas esperadas: SKU, produto, receita, frete, comissão, imposto, custo.",
    )
    data_override = st.text_input(
        "Data de referência",
        placeholder="YYYY-MM-DD  (opcional)",
        label_visibility="visible",
        key="periodo_override",
    )
    if st.button("Processar", type="primary", disabled=uploaded is None,
                 use_container_width=True):
        _processar_upload(uploaded, data_override.strip() or None)


def _processar_upload(uploaded, data_referencia: str | None) -> None:
    suffix = "." + uploaded.name.split(".")[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name
    try:
        result = run_pipeline(tmp_path, data_referencia=data_referencia)
        st.success(
            f"✅ {result['rows_inserted']} SKUs importados — "
            f"{_fmt_periodo(result['periodo'])}. "
            f"{result['rows_skipped']} duplicatas ignoradas."
        )
        threading.Thread(
            target=backup_to_github,
            kwargs={"reason": f"ingestão {uploaded.name}"},
            daemon=True,
        ).start()
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao processar: {e}")
    finally:
        os.unlink(tmp_path)


# ── Layout ───────────────────────────────────────────────────────────────────
_render_header()

periodos = get_periodos()

with st.sidebar:
    st.markdown(
        "<p style='font-size:1.15rem;font-weight:700;"
        "letter-spacing:0.06em;text-transform:uppercase;"
        "text-align:center;margin:1rem 0 0.5rem;padding:0;'>"
        "Filtros</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Período ───────────────────────────────────────────────────────────────
    if periodos:
        periodo = st.selectbox(
            "Período",
            periodos,
            format_func=_fmt_periodo,
            label_visibility="visible",
            key="periodo_global",
        )
    else:
        periodo = None

    # ── Pesquisa ──────────────────────────────────────────────────────────────
    filtro_sku = st.text_input(
        "Pesquisar produto",
        placeholder="SKU ou nome do produto...",
        label_visibility="visible",
        key="filtro_sku",
    )
    if filtro_sku:
        if st.button("✕  Limpar filtro", key="clear_filter", use_container_width=True):
            st.session_state["filtro_sku"] = ""
            st.rerun()

    if periodos:
        st.caption(f"Períodos carregados: **{len(periodos)}** — mais recente: **{_fmt_periodo(periodos[0])}**")

    st.divider()
    _sidebar_import()

# ── Main content ─────────────────────────────────────────────────────────────
if not periodos:
    st.info(
        "Nenhum dado carregado ainda. "
        "Use o painel lateral para importar um relatório CSV ou Excel."
    )
else:
    from app.views import dashboard, abc as abc_page, classificacao, comparativo

    tab1, tab2, tab3, tab4 = st.tabs([
        "Visão Geral",
        "Curva ABC",
        "Classificação",
        "Comparativo",
    ])
    with tab1:
        dashboard.render(periodo, filtro_sku)
    with tab2:
        abc_page.render(periodo, filtro_sku)
    with tab3:
        classificacao.render(periodo, filtro_sku)
    with tab4:
        comparativo.render(periodo, periodos, filtro_sku)

# ── Footer fixo (mesmo padrão devolucoes/expedicao) ──────────────────────────
from datetime import datetime as _dt
st.markdown(
    f'<div style="background:#14283C;border-top:3px solid #BFA168;'
    f'margin-top:3rem;padding:0.6rem 1.75rem;text-align:center;">'
    f'<span style="font-family:Rajdhani,Inter,\'Segoe UI\',sans-serif;'
    f'font-weight:600;font-size:0.82rem;color:rgba(155,172,189,.80);'
    f'letter-spacing:.08em;text-transform:uppercase;">'
    f'Grupo Náutica Refrigeração  ©  {_dt.now().year}'
    f'</span></div>',
    unsafe_allow_html=True,
)
