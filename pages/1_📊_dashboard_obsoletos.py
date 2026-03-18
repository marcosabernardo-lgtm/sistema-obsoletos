import streamlit as st
import pandas as pd
import altair as alt
import os

from analytics.analises import evolucao_estoque
from utils.navbar import render_navbar, render_filtros_topo

from tabs.obsoletos.base_historica import render as render_base_historica
from tabs.obsoletos.top20_produtos import render as render_top20
from tabs.obsoletos.graficos import render as render_graficos
from tabs.obsoletos.movimentacao_obsoleto import render as render_movimentacao
from tabs.obsoletos.evolucao_estoque import render as render_evolucao


st.set_page_config(page_title="Dashboard Estoque", layout="wide")
render_navbar("Dashboard de Estoque Obsoleto")

# -------------------------------------------------
# CSS
# -------------------------------------------------

st.markdown("""
<style>

/* Esconde sidebar */
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }

/* HEADER TABLE */
div[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stDataFrame"] thead th {
    background-color:#0f5a60 !important;
    color:white !important;
    font-weight:600 !important;
    border-bottom: 1px solid #EC6E21 !important;
}

/* ROW COLOR */
div[data-testid="stDataFrame"] div[role="gridcell"]{
    background-color:#0f5a60 !important;
}

/* KPI */
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
st.markdown("---")

# -------------------------------------------------
# FUNÇÕES
# -------------------------------------------------

def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data
def carregar_base(pasta):
    arquivos = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith(".parquet")]
    lista = [pd.read_parquet(arq) for arq in arquivos]
    df_hist = pd.concat(lista, ignore_index=True)
    df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"])
    return df_hist.sort_values("Data Fechamento")


# -------------------------------------------------
# CARREGAR BASE
# -------------------------------------------------

PASTA_OBSOLETOS = "data/obsoletos"

if not os.path.exists(PASTA_OBSOLETOS):
    st.warning("⚠️ Nenhuma base encontrada em **data/obsoletos**.")
    st.stop()

arquivos = [f for f in os.listdir(PASTA_OBSOLETOS) if f.endswith(".parquet")]

if not arquivos:
    st.warning("⚠️ Nenhum arquivo parquet encontrado.")
    st.stop()

df_hist = carregar_base(PASTA_OBSOLETOS)

# -------------------------------------------------
# FILTROS NO TOPO
# -------------------------------------------------

datas_disponiveis = sorted(df_hist["Data Fechamento"].dt.date.unique(), reverse=True)
datas_fmt_list = [d.strftime("%d/%m/%Y") for d in datas_disponiveis]
datas_map = {d.strftime("%d/%m/%Y"): d for d in datas_disponiveis}

# Pré-carrega opções para o fechamento mais recente
data_preview = pd.Timestamp(datas_disponiveis[0])
df_preview = df_hist[df_hist["Data Fechamento"] == data_preview]
empresas_disponiveis = sorted(df_preview["Empresa / Filial"].dropna().unique())

# Contas dinâmicas conforme empresas já selecionadas
empresas_ja_sel = st.session_state.get("obsoletos_empresas", [])
df_temp_conta = df_preview.copy()
if empresas_ja_sel:
    df_temp_conta = df_temp_conta[df_temp_conta["Empresa / Filial"].isin(empresas_ja_sel)]
contas_disponiveis = sorted(df_temp_conta["Conta"].dropna().unique())

filtros = render_filtros_topo(
    datas=datas_fmt_list,
    empresas=empresas_disponiveis,
    extras={"Conta": contas_disponiveis} if contas_disponiveis else None,
    key_prefix="obsoletos"
)

data_selecionada = pd.Timestamp(datas_map[filtros["data"]])
empresas_sel     = filtros["empresas"]
contas_sel       = filtros.get("conta", [])

# -------------------------------------------------
# APLICA FILTROS
# -------------------------------------------------

df_kpi = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()

if empresas_sel:
    df_kpi = df_kpi[df_kpi["Empresa / Filial"].isin(empresas_sel)]
if contas_sel:
    df_kpi = df_kpi[df_kpi["Conta"].isin(contas_sel)]

# Disponibiliza o df completo para a aba Base Histórica
st.session_state["df_kpi_completo"] = df_kpi

# -------------------------------------------------
# BASE FILTRADA
# -------------------------------------------------

df_filtrado = df_kpi[df_kpi["Status Estoque"] == "Obsoleto"].copy()

# -------------------------------------------------
# KPIs
# -------------------------------------------------

estoque_total    = df_kpi["Custo Total"].sum()
estoque_obsoleto = df_kpi[df_kpi["Status Estoque"] == "Obsoleto"]["Custo Total"].sum()
perc_obsoleto    = estoque_obsoleto / estoque_total if estoque_total > 0 else 0
itens_obsoletos  = df_kpi[df_kpi["Status Estoque"] == "Obsoleto"]["Produto"].nunique()

col1, col2, col3, col4 = st.columns(4)

col1.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Valor Estoque</div>
<div class="kpi-value">{moeda_br(estoque_total)}</div>
</div>
""", unsafe_allow_html=True)

col2.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Estoque Obsoleto</div>
<div class="kpi-value">{moeda_br(estoque_obsoleto)}</div>
</div>
""", unsafe_allow_html=True)

col3.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">% Estoque Obsoleto</div>
<div class="kpi-value">{perc_obsoleto*100:.2f}%</div>
</div>
""", unsafe_allow_html=True)

col4.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Itens Obsoletos</div>
<div class="kpi-value">{itens_obsoletos}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# BASE HISTÓRICA FILTRADA
# -------------------------------------------------

df_hist_filtrado = df_hist.copy()
if empresas_sel:
    df_hist_filtrado = df_hist_filtrado[df_hist_filtrado["Empresa / Filial"].isin(empresas_sel)]
if contas_sel:
    df_hist_filtrado = df_hist_filtrado[df_hist_filtrado["Conta"].isin(contas_sel)]

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📚 Base Histórica",
    "📈 Evolução do Estoque",
    "🔄 Movimentação do Obsoleto",
    "🏆 Top 20 Produtos",
    "📊 Gráficos"
])

with tab1:
    render_base_historica(df_filtrado, moeda_br)

with tab2:
    render_evolucao(df_hist_filtrado, moeda_br)

with tab3:
    render_movimentacao(df_hist_filtrado, moeda_br, data_selecionada)

with tab4:
    render_top20(df_filtrado, moeda_br)

with tab5:
    render_graficos(df_filtrado, moeda_br)
