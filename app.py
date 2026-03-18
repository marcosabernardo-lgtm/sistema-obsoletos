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
.block-container { padding: 2rem 3rem 1rem !important; max-width: 100% !important; }

.home-header {
    background: linear-gradient(135deg, #013A42 0%, #024E58 60%, #015A66 100%);
    border-bottom: 1px solid rgba(236,110,33,0.25);
    padding: 40px 48px 36px;
    border-radius: 16px;
    margin-bottom: 32px;
    position: relative; overflow: hidden;
}
.home-header::before {
    content:''; position:absolute; top:-60px; right:-60px;
    width:280px; height:280px; border-radius:50%;
    background:radial-gradient(circle,rgba(236,110,33,0.08) 0%,transparent 70%);
    pointer-events:none;
}
.header-eyebrow {
    font-family:'JetBrains Mono',monospace; font-size:10px;
    font-weight:600; letter-spacing:3px; text-transform:uppercase;
    color:#EC6E21; margin-bottom:10px;
}
.header-title {
    font-size:32px; font-weight:700; color:#FFFFFF;
    line-height:1.15; margin-bottom:10px; letter-spacing:-0.3px;
}
.header-title span { color:#EC6E21; }
.header-subtitle {
    font-size:13px; font-weight:300; color:rgba(255,255,255,0.5);
    max-width:480px; line-height:1.6;
}

.section-label {
    font-family:'JetBrains Mono',monospace; font-size:9px;
    font-weight:600; letter-spacing:3px; text-transform:uppercase;
    color:rgba(255,255,255,0.22); margin-bottom:14px;
}

/* Card via botão nativo do Streamlit */
div[data-testid="stButton"] > button {
    width: 100% !important;
    background: linear-gradient(145deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0.02) 100%) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 14px !important;
    padding: 22px 20px 18px !important;
    text-align: left !important;
    color: white !important;
    font-family: 'Sora', sans-serif !important;
    transition: all 0.2s ease !important;
    height: auto !important;
    min-height: 0 !important;
    white-space: normal !important;
    line-height: 1.4 !important;
    cursor: pointer !important;
}
div[data-testid="stButton"] > button:hover {
    background: linear-gradient(145deg, rgba(255,255,255,0.09) 0%, rgba(255,255,255,0.04) 100%) !important;
    border-color: rgba(255,255,255,0.18) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important;
}
div[data-testid="stButton"] > button:focus {
    box-shadow: none !important;
    outline: none !important;
}

/* Cores por card — usando classe no container pai */
.card-obs > div[data-testid="stButton"] > button { border-top: 2px solid #EC6E21 !important; }
.card-est > div[data-testid="stButton"] > button { border-top: 2px solid #00C9E0 !important; }
.card-dio > div[data-testid="stButton"] > button { border-top: 2px solid #9B7BFF !important; }
.card-inv > div[data-testid="stButton"] > button { border-top: 2px solid #2ECC71 !important; }
.card-cfg > div[data-testid="stButton"] > button { border-top: 2px solid rgba(255,255,255,0.25) !important; }

.home-footer {
    padding: 16px 0;
    border-top: 1px solid rgba(255,255,255,0.06);
    display: flex; align-items: center; justify-content: space-between;
    margin-top: 24px;
}
.footer-mono {
    font-family:'JetBrains Mono',monospace; font-size:10px;
    color:rgba(255,255,255,0.2); letter-spacing:1.5px;
}
.status-dot {
    display:inline-block; width:6px; height:6px; border-radius:50%;
    background:#2ECC71; box-shadow:0 0 6px #2ECC71;
    margin-right:6px; vertical-align:middle;
}
</style>
""", unsafe_allow_html=True)

# ── HEADER ───────────────────────────────────────────────

st.markdown("""
<div class="home-header">
    <div class="header-eyebrow">Grupo Alltech · Inteligência de Estoques</div>
    <div class="header-title">Análise Gerencial de <span>Estoques</span></div>
    <div class="header-subtitle">
        Consolidação estratégica com análise de obsolescência,
        evolução histórica, DIO por produto e controle de inventário.
    </div>
</div>
""", unsafe_allow_html=True)

# ── CARDS ────────────────────────────────────────────────

st.markdown('<div class="section-label">Módulos do sistema</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown('<div class="card-obs">', unsafe_allow_html=True)
    if st.button("📊  Estoque Obsoleto\n\nIdentificação de itens sem movimentação, ranking de produtos críticos e evolução histórica.", key="btn_obs"):
        st.switch_page("pages/1_📊_dashboard_obsoletos.py")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card-est">', unsafe_allow_html=True)
    if st.button("📦  Evolução de Estoque\n\nAcompanhamento do valor total em estoque ao longo do tempo, por empresa e filial.", key="btn_est"):
        st.switch_page("pages/2_📦_dashboard_estoque.py")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="card-dio">', unsafe_allow_html=True)
    if st.button("⏱️  DIO — Dias de Estoque\n\nDays Inventory Outstanding por produto. Quantos dias de consumo o estoque representa.", key="btn_dio"):
        st.switch_page("pages/3_📦_dashboard_dio.py")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

col4, col5, col6 = st.columns(3, gap="medium")

with col4:
    st.markdown('<div class="card-inv">', unsafe_allow_html=True)
    if st.button("🗂️  Inventário\n\nControle e acompanhamento de inventários físicos por empresa e período.", key="btn_inv"):
        st.switch_page("pages/4_📊_dashboard_inventario.py")
    st.markdown('</div>', unsafe_allow_html=True)

with col5:
    st.markdown('<div class="card-cfg">', unsafe_allow_html=True)
    if st.button("⚙️  Configurador\n\nProcessamento de fechamentos mensais, atualização das bases e administração do sistema.", key="btn_cfg"):
        st.switch_page("pages/0_⚙️_configurador.py")
    st.markdown('</div>', unsafe_allow_html=True)

with col6:
    st.markdown("<div></div>", unsafe_allow_html=True)

# ── FOOTER ───────────────────────────────────────────────

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
