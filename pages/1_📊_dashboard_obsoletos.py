import streamlit as st
import pandas as pd
import altair as alt
import os

from analytics.analises import evolucao_estoque
from utils.navbar import render_navbar

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

/* SIDEBAR */

section[data-testid="stSidebar"]{
    width:260px !important;
}

/* FILTROS */

section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {
    border: 2px solid #EC6E21 !important;
    border-radius: 8px !important;
    background-color: #005562 !important;
    color: white !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] span,
section[data-testid="stSidebar"] div[data-baseweb="select"] div {
    color: white !important;
}

section[data-testid="stSidebar"] label {
    color: white !important;
    font-weight: 600 !important;
}

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

.kpi-title{
    font-size:14px;
    color:white;
}

.kpi-value{
    font-size:26px;
    font-weight:700;
    color:white;
}

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

    arquivos = [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if f.endswith(".parquet")
    ]

    lista = []

    for arq in arquivos:
        df = pd.read_parquet(arq)
        lista.append(df)

    df_hist = pd.concat(lista, ignore_index=True)

    df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"])
    df_hist = df_hist.sort_values("Data Fechamento")

    return df_hist


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
# FILTROS (DINÂMICOS)
# -------------------------------------------------

st.sidebar.header("Filtros")

datas_disponiveis = sorted(df_hist["Data Fechamento"].dt.date.unique(), reverse=True)

datas_fmt = {
    d.strftime("%d/%m/%Y"): d for d in datas_disponiveis
}

data_sel = st.sidebar.selectbox(
    "Data de Fechamento",
    options=list(datas_fmt.keys()),
    index=0
)

data_selecionada = pd.Timestamp(datas_fmt[data_sel])

# BASE INICIAL
df_base_filtros = df_hist[
    df_hist["Data Fechamento"] == data_selecionada
].copy()

# EMPRESA
empresas_opcoes = sorted(df_base_filtros["Empresa / Filial"].dropna().unique())

empresas_sel = st.sidebar.multiselect(
    "Empresa / Filial",
    empresas_opcoes
)

df_temp = df_base_filtros.copy()

if empresas_sel:
    df_temp = df_temp[df_temp["Empresa / Filial"].isin(empresas_sel)]

# CONTA (DINÂMICO)
contas_opcoes = sorted(df_temp["Conta"].dropna().unique())

contas_sel = st.sidebar.multiselect(
    "Conta",
    contas_opcoes
)

if contas_sel:
    df_temp = df_temp[df_temp["Conta"].isin(contas_sel)]

# RESULTADO FINAL
df_kpi = df_temp.copy()

# Disponibiliza o df completo
st.session_state["df_kpi_completo"] = df_kpi

# -------------------------------------------------
# BASE FILTRADA
# -------------------------------------------------

df_filtrado = df_kpi[df_kpi["Status Estoque"] == "Obsoleto"].copy()

# -------------------------------------------------
# KPIs
# -------------------------------------------------

estoque_total = df_kpi["Custo Total"].sum()

estoque_obsoleto = df_kpi[
    df_kpi["Status Estoque"] == "Obsoleto"
]["Custo Total"].sum()

perc_obsoleto = (
    estoque_obsoleto / estoque_total if estoque_total > 0 else 0
)

itens_obsoletos = df_kpi[
    df_kpi["Status Estoque"] == "Obsoleto"
]["Produto"].nunique()

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
    df_hist_filtrado = df_hist_filtrado[
        df_hist_filtrado["Empresa / Filial"].isin(empresas_sel)
    ]

if contas_sel:
    df_hist_filtrado = df_hist_filtrado[
        df_hist_filtrado["Conta"].isin(contas_sel)
    ]

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