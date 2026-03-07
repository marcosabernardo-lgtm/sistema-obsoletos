import streamlit as st
import pandas as pd
import altair as alt
import os

from analytics.analises import evolucao_estoque

from tabs.obsoletos.base_historica import render as render_base_historica
from tabs.obsoletos.evolucao_estoque import render as render_evolucao
from tabs.obsoletos.top20_produtos import render as render_top20
from tabs.obsoletos.graficos import render as render_graficos
from tabs.obsoletos.movimentacao_obsoleto import render as render_movimentacao



st.set_page_config(page_title="Dashboard Estoque", layout="wide")

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
div[data-testid="stDataFrame"] [role="columnheader"] span,
div[data-testid="stDataFrame"] [role="columnheader"] div,
div[data-testid="stDataFrame"] [role="columnheader"] p,
div[data-testid="stDataFrame"] thead th,
div[data-testid="stDataFrame"] .dvn-col-gutter,
div[data-testid="stDataFrame"] .sticky {
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

# -------------------------------------------------
# CARREGAR BASE
# -------------------------------------------------

BASE_PATH = "data/base_historica.parquet"

if not os.path.exists(BASE_PATH):
    st.warning("⚠️ Nenhuma base de dados encontrada. Acesse a página **app** para fazer o upload dos arquivos.")
    st.stop()

df_hist = pd.read_parquet(BASE_PATH)


# -------------------------------------------------
# FILTROS
# -------------------------------------------------

st.sidebar.header("Filtros")

status_estoque = st.sidebar.selectbox(
    "Status do Estoque",
    ["Geral","Obsoletos"]
)

empresas_sel = st.sidebar.multiselect(
    "Empresa / Filial",
    sorted(df_hist["Empresa / Filial"].dropna().unique())
)

contas_sel = st.sidebar.multiselect(
    "Conta",
    sorted(df_hist["Conta"].dropna().unique())
)

# -------------------------------------------------
# BASE KPI
# -------------------------------------------------

df_kpi = df_hist.copy()

if empresas_sel:
    df_kpi = df_kpi[df_kpi["Empresa / Filial"].isin(empresas_sel)]

if contas_sel:
    df_kpi = df_kpi[df_kpi["Conta"].isin(contas_sel)]

# -------------------------------------------------
# BASE FILTRADA
# -------------------------------------------------

df_filtrado = df_kpi.copy()

if status_estoque == "Obsoletos":
    df_filtrado = df_filtrado[
        df_filtrado["Status do Movimento"] != "Até 6 meses"
    ]

# -------------------------------------------------
# KPIs
# -------------------------------------------------

if not df_kpi.empty:
    ultima_data = df_kpi["Data Fechamento"].max()
    base_kpi = df_kpi[df_kpi["Data Fechamento"] == ultima_data]

    estoque_total = base_kpi["Custo Total"].sum()

    estoque_obsoleto = base_kpi[
        base_kpi["Status do Movimento"] != "Até 6 meses"
    ]["Custo Total"].sum()

    perc_obsoleto = estoque_obsoleto / estoque_total if estoque_total > 0 else 0

    itens_obsoletos = base_kpi[
        base_kpi["Status do Movimento"] != "Até 6 meses"
    ]["Produto"].nunique()
else:
    estoque_total = 0
    estoque_obsoleto = 0
    perc_obsoleto = 0
    itens_obsoletos = 0

col1,col2,col3,col4 = st.columns(4)

col1.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Valor Estoque</div>
<div class="kpi-value">{moeda_br(estoque_total)}</div>
</div>
""",unsafe_allow_html=True)

col2.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Estoque Obsoleto</div>
<div class="kpi-value">{moeda_br(estoque_obsoleto)}</div>
</div>
""",unsafe_allow_html=True)

col3.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">% Estoque Obsoleto</div>
<div class="kpi-value">{perc_obsoleto*100:.2f}%</div>
</div>
""",unsafe_allow_html=True)

col4.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Itens Obsoletos</div>
<div class="kpi-value">{itens_obsoletos}</div>
</div>
""",unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "📚 Base Histórica",
    "📈 Evolução do Estoque",
    "🔄 Movimentação do Obsoleto",
    "🏆 Top 20 Produtos",
    "📊 Gráficos"
])

with tab1:
    render_base_historica(df_filtrado, moeda_br)

with tab2:
    render_evolucao(df_kpi, moeda_br)

with tab3:
    render_movimentacao(df_kpi, moeda_br)

with tab4:
    render_top20(df_filtrado, moeda_br)

with tab5:
    render_graficos(df_filtrado, moeda_br)