import streamlit as st
import pandas as pd

from utils.navbar import render_navbar, render_filtros_topo

from tabs.obsoletos.base_historica import render as render_base_historica
from tabs.obsoletos.top20_produtos import render as render_top20
from tabs.obsoletos.graficos import render as render_graficos
from tabs.obsoletos.movimentacao_obsoleto import render as render_movimentacao
from tabs.obsoletos.evolucao_estoque import render as render_evolucao
from tabs.obsoletos.proximos_obsoletos import render as render_proximos

st.set_page_config(page_title="Dashboard Estoque", layout="wide")
render_navbar("Dashboard de Estoque Obsoleto")

# -------------------------------------------------
# CSS
# -------------------------------------------------

st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }

div[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stDataFrame"] thead th {
    background-color:#0f5a60 !important;
    color:white !important;
    font-weight:600 !important;
    border-bottom: 1px solid #EC6E21 !important;
}
div[data-testid="stDataFrame"] div[role="gridcell"]{
    background-color:#0f5a60 !important;
}
.kpi-card{
    background-color:#005562;
    border:2px solid #EC6E21;
    padding:16px;
    border-radius:10px;
    text-align:center;
}
.kpi-title{ font-size:14px; color:white; }
.kpi-value{ font-size:26px; font-weight:700; color:white; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard de Estoque Obsoleto")
st.markdown("""
<p style="
    color: rgba(255,255,255,0.45);
    font-size: 14px;
    font-style: italic;
    letter-spacing: 0.5px;
    margin-top: -12px;
    margin-bottom: 8px;
    border-left: 3px solid #EC6E21;
    padding-left: 10px;
">
    Itens que estão no estoque sem movimentação há mais de 180 dias.
</p>
""", unsafe_allow_html=True)
st.markdown("---")

# -------------------------------------------------
# FUNÇÕES
# -------------------------------------------------

def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# -------------------------------------------------
# CARREGAR BASE
# -------------------------------------------------

@st.cache_data(ttl=60, show_spinner="Carregando dados...")
def carregar_base():
    from motor.motor_obsoletos import executar_motor
    df, _ = executar_motor()
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"])
    return df.sort_values("Data Fechamento")

# -------------------------------------------------
# CARREGAMENTO
# -------------------------------------------------

try:
    df_hist = carregar_base()
except Exception as e:
    st.error("Erro ao carregar dados.")
    st.stop()

if df_hist.empty:
    st.warning("⚠️ Base de dados vazia.")
    st.stop()

# -------------------------------------------------
# FILTROS DE TOPO
# -------------------------------------------------

datas_disponiveis = sorted(df_hist["Data Fechamento"].dt.date.unique(), reverse=True)
datas_fmt_list    = [d.strftime("%d/%m/%Y") for d in datas_disponiveis]
datas_map         = {d.strftime("%d/%m/%Y"): d for d in datas_disponiveis}

data_preview_str  = st.session_state.get("obsoletos_data", datas_fmt_list[0])
data_preview      = pd.Timestamp(datas_map.get(data_preview_str, datas_disponiveis[0]))
df_preview        = df_hist[df_hist["Data Fechamento"] == data_preview]
empresas_disponiveis = sorted(df_preview["Empresa / Filial"].dropna().unique())

ef_ja_sel     = st.session_state.get("obsoletos_empresa_sel", [])
filial_ja_sel = st.session_state.get("obsoletos_filial_sel",  [])
contas_ja_sel = st.session_state.get("obsoletos_conta", [])

ef_ativos = [
    ef for ef in empresas_disponiveis
    if (not ef_ja_sel     or ef.split(" / ")[0].strip() in ef_ja_sel)
    and (not filial_ja_sel or ef.split(" / ")[1].strip() in filial_ja_sel)
] if (ef_ja_sel or filial_ja_sel) else list(empresas_disponiveis)

df_filtrado_opcoes = df_preview[df_preview["Empresa / Filial"].isin(ef_ativos)]
contas_disponiveis = sorted(df_filtrado_opcoes["Conta"].dropna().unique())

df_tipo_opcoes = df_filtrado_opcoes.copy()
if contas_ja_sel:
    df_tipo_opcoes = df_tipo_opcoes[df_tipo_opcoes["Conta"].isin(contas_ja_sel)]
tipos_disponiveis = sorted(df_tipo_opcoes["Tipo de Estoque"].dropna().unique())

extras = {}
if contas_disponiveis:
    extras["Conta"] = contas_disponiveis
if tipos_disponiveis:
    extras["Tipo de Estoque"] = tipos_disponiveis

filtros = render_filtros_topo(
    datas=datas_fmt_list,
    empresas=empresas_disponiveis,
    extras=extras if extras else None,
    key_prefix="obsoletos"
)

data_selecionada = pd.Timestamp(datas_map[filtros["data"]])
empresas_sel     = filtros["empresas"]
contas_sel       = filtros.get("conta", [])
tipos_sel        = filtros.get("tipo_de_estoque", [])

# -------------------------------------------------
# BASE FILTRADA (KPIs)
# -------------------------------------------------

df_kpi = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()
if empresas_sel:
    df_kpi = df_kpi[df_kpi["Empresa / Filial"].isin(empresas_sel)]
if contas_sel:
    df_kpi = df_kpi[df_kpi["Conta"].isin(contas_sel)]
if tipos_sel:
    df_kpi = df_kpi[df_kpi["Tipo de Estoque"].isin(tipos_sel)]

df_hist_filtrado = df_hist.copy()
if empresas_sel:
    df_hist_filtrado = df_hist_filtrado[df_hist_filtrado["Empresa / Filial"].isin(empresas_sel)]
if contas_sel:
    df_hist_filtrado = df_hist_filtrado[df_hist_filtrado["Conta"].isin(contas_sel)]
if tipos_sel:
    df_hist_filtrado = df_hist_filtrado[df_hist_filtrado["Tipo de Estoque"].isin(tipos_sel)]

df_obsoleto_base = df_kpi[df_kpi["Status Estoque"] == "Obsoleto"].copy()

# -------------------------------------------------
# KPIs
# -------------------------------------------------

estoque_total    = df_kpi["Custo Total"].sum()
estoque_obsoleto = df_obsoleto_base["Custo Total"].sum()
perc_obsoleto    = estoque_obsoleto / estoque_total if estoque_total > 0 else 0
itens_obsoletos  = df_obsoleto_base["Produto"].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.markdown(f"""<div class="kpi-card"><div class="kpi-title">Valor Estoque</div><div class="kpi-value">{moeda_br(estoque_total)}</div></div>""", unsafe_allow_html=True)
col2.markdown(f"""<div class="kpi-card"><div class="kpi-title">Estoque Obsoleto</div><div class="kpi-value">{moeda_br(estoque_obsoleto)}</div></div>""", unsafe_allow_html=True)
col3.markdown(f"""<div class="kpi-card"><div class="kpi-title">% Estoque Obsoleto</div><div class="kpi-value">{perc_obsoleto*100:.2f}%</div></div>""", unsafe_allow_html=True)
col4.markdown(f"""<div class="kpi-card"><div class="kpi-title">Itens Obsoletos</div><div class="kpi-value">{itens_obsoletos}</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📚 Base Histórica",
    "📈 Evolução do Estoque",
    "🔄 Movimentação do Obsoleto",
    "⚠️ Próximos Obsoletos",
    "🏆 Top 20 Produtos",
    "📊 Resumos"
])

with tab1:
    col_vis, col_info = st.columns([2, 3])
    with col_vis:
        visao_base = st.radio(
            "Visualizar itens:",
            options=["Apenas Obsoletos", "Geral (Todo o Estoque)"],
            horizontal=True,
            key="visao_base_historica"
        )
    
    if visao_base == "Apenas Obsoletos":
        df_para_tabela = df_obsoleto_base
        st.caption(f"Exibindo apenas itens com status **Obsoleto**")
    else:
        df_para_tabela = df_kpi
        st.caption(f"Exibindo **todo o estoque** (Giro + Obsoletos)")

    render_base_historica(df_para_tabela, moeda_br)

with tab2:
    render_evolucao(df_hist_filtrado, moeda_br)

with tab3:
    render_movimentacao(df_hist_filtrado, moeda_br, data_selecionada)

with tab4:
    render_proximos(df_kpi, moeda_br)

with tab5:
    render_top20(df_obsoleto_base, moeda_br)

with tab6:
    render_graficos(df_obsoleto_base, moeda_br, df_hist_filtrado)