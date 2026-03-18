import streamlit as st
import os

st.set_page_config(
    page_title="Grupo Alltech — Gestão de Estoques",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background-color: #02404A !important;
    font-family: 'Sora', sans-serif;
}

[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── HEADER ── */
.home-header {
    background: linear-gradient(135deg, #013A42 0%, #024E58 50%, #015A66 100%);
    border-bottom: 1px solid rgba(236, 110, 33, 0.25);
    padding: 52px 64px 44px;
    position: relative;
    overflow: hidden;
}

.home-header::before {
    content: '';
    position: absolute;
    top: -80px; right: -80px;
    width: 350px; height: 350px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(236,110,33,0.07) 0%, transparent 70%);
    pointer-events: none;
}

.header-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #EC6E21;
    margin-bottom: 14px;
}

.header-title {
    font-size: 40px;
    font-weight: 700;
    color: #FFFFFF;
    line-height: 1.1;
    margin-bottom: 12px;
    letter-spacing: -0.5px;
}

.header-title span { color: #EC6E21; }

.header-subtitle {
    font-size: 15px;
    font-weight: 300;
    color: rgba(255,255,255,0.5);
    max-width: 500px;
    line-height: 1.65;
}

/* ── SECTION ── */
.cards-section {
    padding: 48px 64px 32px;
}

.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.25);
    margin-bottom: 20px;
}

/* ── CARD ── */
.nav-card {
    background: linear-gradient(145deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    padding: 30px 28px 26px;
    position: relative;
    overflow: hidden;
    transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
    height: 100%;
    min-height: 200px;
}

.nav-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent);
    opacity: 0;
    transition: opacity 0.22s;
    border-radius: 18px 18px 0 0;
}

.nav-card:hover {
    background: linear-gradient(145deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.035) 100%);
    border-color: rgba(255,255,255,0.13);
    transform: translateY(-4px);
    box-shadow: 0 16px 48px rgba(0,0,0,0.35);
}

.nav-card:hover::after { opacity: 1; }

.card-icon {
    width: 50px; height: 50px;
    border-radius: 12px;
    background: var(--icon-bg);
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
    margin-bottom: 18px;
}

.card-title {
    font-size: 17px;
    font-weight: 600;
    color: #FFFFFF;
    margin-bottom: 8px;
}

.card-desc {
    font-size: 13px;
    font-weight: 300;
    color: rgba(255,255,255,0.42);
    line-height: 1.55;
    margin-bottom: 22px;
}

.card-cta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    color: var(--accent);
    text-transform: uppercase;
    opacity: 0.8;
}

/* Cores por card */
.c-obs  { --accent: #EC6E21; --icon-bg: rgba(236,110,33,0.13); }
.c-est  { --accent: #00C9E0; --icon-bg: rgba(0,201,224,0.12); }
.c-dio  { --accent: #9B7BFF; --icon-bg: rgba(155,123,255,0.12); }
.c-inv  { --accent: #2ECC71; --icon-bg: rgba(46,204,113,0.12); }
.c-cfg  { --accent: rgba(255,255,255,0.4); --icon-bg: rgba(255,255,255,0.07); }

/* Sobrepõe botão invisível sobre o card */
div[data-testid="column"] {
    position: relative;
}

.stButton { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
.stButton > button {
    width: 100% !important;
    height: 100% !important;
    opacity: 0 !important;
    position: absolute !important;
    top: 0 !important; left: 0 !important;
    cursor: pointer !important;
    z-index: 5 !important;
}

/* ── FOOTER ── */
.home-footer {
    padding: 20px 64px;
    border-top: 1px solid rgba(255,255,255,0.05);
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 16px;
}

.footer-mono {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: rgba(255,255,255,0.2);
    letter-spacing: 1.5px;
}

.status-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #2ECC71;
    box-shadow: 0 0 8px #2ECC71;
    margin-right: 7px;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)


# ── HEADER ────────────────────────────────────────────────

st.markdown("""
<div class="home-header">
    <div class="header-eyebrow">Grupo Alltech · Inteligência de Estoques</div>
    <div class="header-title">Análise Gerencial<br>de <span>Estoques</span></div>
    <div class="header-subtitle">
        Consolidação estratégica com análise de obsolescência,
        evolução histórica, DIO por produto e controle de inventário.
    </div>
</div>
""", unsafe_allow_html=True)


# ── CARDS ─────────────────────────────────────────────────

st.markdown('<div class="cards-section">', unsafe_allow_html=True)
st.markdown('<div class="section-label">Módulos do sistema</div>', unsafe_allow_html=True)

# Linha 1 — 3 cards
col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown("""
    <div class="nav-card c-obs">
        <div class="card-icon">📊</div>
        <div class="card-title">Estoque Obsoleto</div>
        <div class="card-desc">Identificação de itens sem movimentação, ranking de produtos críticos e evolução histórica da obsolescência.</div>
        <div class="card-cta">Acessar →</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(" ", key="btn_obs"):
        st.switch_page("pages/1_📊_dashboard_obsoletos.py")

with col2:
    st.markdown("""
    <div class="nav-card c-est">
        <div class="card-icon">📦</div>
        <div class="card-title">Evolução de Estoque</div>
        <div class="card-desc">Acompanhamento do valor total em estoque ao longo do tempo, segmentado por empresa e filial.</div>
        <div class="card-cta">Acessar →</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(" ", key="btn_est"):
        st.switch_page("pages/2_📦_dashboard_estoque.py")

with col3:
    st.markdown("""
    <div class="nav-card c-dio">
        <div class="card-icon">⏱️</div>
        <div class="card-title">DIO — Dias de Estoque</div>
        <div class="card-desc">Days Inventory Outstanding por produto. Mede quantos dias de consumo o estoque atual representa.</div>
        <div class="card-cta">Acessar →</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(" ", key="btn_dio"):
        st.switch_page("pages/3_📦_dashboard_dio.py")

st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)

# Linha 2 — 2 cards + espaço
col4, col5, col6 = st.columns(3, gap="medium")

with col4:
    st.markdown("""
    <div class="nav-card c-inv">
        <div class="card-icon">🗂️</div>
        <div class="card-title">Inventário</div>
        <div class="card-desc">Controle e acompanhamento de inventários físicos realizados por empresa e período.</div>
        <div class="card-cta">Acessar →</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(" ", key="btn_inv"):
        st.switch_page("pages/4_🗂️_dashboard_inventario.py")

with col5:
    st.markdown("""
    <div class="nav-card c-cfg">
        <div class="card-icon">⚙️</div>
        <div class="card-title">Configurador</div>
        <div class="card-desc">Processamento de fechamentos mensais, atualização das bases de dados e administração do sistema.</div>
        <div class="card-cta">Acessar →</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(" ", key="btn_cfg"):
        st.switch_page("pages/0_⚙️_configurador.py")

with col6:
    st.markdown("<div></div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


# ── FOOTER ────────────────────────────────────────────────

obs_ok = os.path.exists("data/obsoletos") and bool([f for f in os.listdir("data/obsoletos") if f.endswith(".parquet")]) if os.path.exists("data/obsoletos") else False
est_ok = os.path.exists("data/estoque")   and bool([f for f in os.listdir("data/estoque")   if f.endswith(".parquet")]) if os.path.exists("data/estoque")   else False
dio_ok = os.path.exists("data/dio")       and bool([f for f in os.listdir("data/dio")       if f.endswith(".parquet")]) if os.path.exists("data/dio")       else False

bases = []
if obs_ok: bases.append("Obsoletos ✓")
if est_ok: bases.append("Estoque ✓")
if dio_ok: bases.append("DIO ✓")
bases_str = " · ".join(bases) if bases else "Nenhuma base carregada"

st.markdown(f"""
<div class="home-footer">
    <div class="footer-mono"><span class="status-dot"></span>SISTEMA ONLINE</div>
    <div class="footer-mono">{bases_str}</div>
    <div class="footer-mono">GRUPO ALLTECH © 2026</div>
</div>
""", unsafe_allow_html=True)