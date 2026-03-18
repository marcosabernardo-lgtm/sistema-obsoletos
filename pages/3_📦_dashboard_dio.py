import streamlit as st
import pandas as pd
import os
import numpy as np

from utils.navbar import render_navbar, render_filtros_topo

from tabs.dio.distribuicao_faixa import render as render_distribuicao
from tabs.dio.top20 import render as render_top20
from tabs.dio.todos_produtos import render as render_todos_produtos
from tabs.dio.cruzamento_obsoletos import render as render_cruzamento
from tabs.dio.base_historica import render as render_base_historica

st.set_page_config(page_title="Dashboard DIO", layout="wide")
render_navbar("Dashboard DIO")

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
    min-height:100px;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    gap:4px;
}

.kpi-title{
    font-size:13px;
    color:white;
    line-height:1.2;
    white-space:nowrap;
}

.kpi-value{
    font-size:22px;
    font-weight:700;
    color:white;
    line-height:1.2;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    width:100%;
}

</style>
""", unsafe_allow_html=True)

st.title("📦 Dashboard DIO — Days Inventory Outstanding")
st.markdown("---")

# -------------------------------------------------
# HELPERS
# -------------------------------------------------

def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_numero(valor):
    return f"{valor:,.0f}".replace(",", ".")

ORDEM_FAIXAS = [
    "Até 30 dias",
    "31–90 dias",
    "91–180 dias",
    "181–365 dias",
    "+ 1 ano",
    "Sem consumo"
]

def categorizar_dio(dio):
    if dio == np.inf or pd.isna(dio):
        return "Sem consumo"
    if dio <= 30:   return "Até 30 dias"
    if dio <= 90:   return "31–90 dias"
    if dio <= 180:  return "91–180 dias"
    if dio <= 365:  return "181–365 dias"
    return "+ 1 ano"

def formatar_dio(dio):
    if dio == np.inf or pd.isna(dio):
        return "Sem consumo"
    dias  = int(round(dio))
    anos  = dias // 365
    meses = (dias % 365) // 30
    d     = (dias % 365) % 30
    partes = []
    if anos:  partes.append(f"{anos} ano{'s' if anos > 1 else ''}")
    if meses: partes.append(f"{meses} {'meses' if meses > 1 else 'mês'}")
    if d or not partes: partes.append(f"{d} dia{'s' if d != 1 else ''}")
    return " ".join(partes)

# -------------------------------------------------
# CARREGAR BASE
# -------------------------------------------------

@st.cache_data
def carregar_base(pasta):
    arquivos = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith(".parquet")]
    df_all = pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)
    df_all["Data Fechamento"] = pd.to_datetime(df_all["Data Fechamento"])
    return df_all.sort_values("Data Fechamento")


PASTA_DIO = "data/dio"

if not os.path.exists(PASTA_DIO):
    st.warning("⚠️ Nenhuma base encontrada em **data/dio**. Processe o DIO primeiro no Configurador.")
    st.stop()

arquivos = [f for f in os.listdir(PASTA_DIO) if f.endswith(".parquet")]

if not arquivos:
    st.warning("⚠️ Nenhum arquivo parquet encontrado em **data/dio**.")
    st.stop()

df_all = carregar_base(PASTA_DIO)

# -------------------------------------------------
# FILTROS NO TOPO
# -------------------------------------------------

datas_disponiveis = sorted(df_all["Data Fechamento"].dt.date.unique(), reverse=True)
datas_fmt_list = [d.strftime("%d/%m/%Y") for d in datas_disponiveis]
datas_map = {d.strftime("%d/%m/%Y"): d for d in datas_disponiveis}

data_preview = pd.Timestamp(datas_disponiveis[0])
df_preview = df_all[df_all["Data Fechamento"] == data_preview]
empresas_disponiveis = sorted(df_preview["Empresa / Filial"].dropna().unique())

filtros = render_filtros_topo(
    datas=datas_fmt_list,
    empresas=empresas_disponiveis,
    extras={"Faixa DIO": ORDEM_FAIXAS},
    key_prefix="dio"
)

data_selecionada = pd.Timestamp(datas_map[filtros["data"]])
empresas_sel     = filtros["empresas"]
faixas_sel       = filtros.get("faixa_dio", [])

# -------------------------------------------------
# BASE FILTRADA
# -------------------------------------------------

df = df_all[df_all["Data Fechamento"] == data_selecionada].copy()

if empresas_sel:
    df = df[df["Empresa / Filial"].isin(empresas_sel)]

# -------------------------------------------------
# MODO
# -------------------------------------------------

if "modo_dio" not in st.session_state:
    st.session_state["modo_dio"] = "Por Qtd"

modo = st.session_state["modo_dio"]

if modo == "Por Valor":
    df["Consumo_Diario_Valor"] = df["Consumo_Diario"] * df["Vlr Unit"]
    df["DIO_calc"] = np.where(
        df["Consumo_Diario_Valor"] > 0,
        df["Custo Total"] / df["Consumo_Diario_Valor"],
        np.inf
    )
    label_eixo    = "DIO Valor (dias)"
    label_consumo = "Consumo 12m (R$)"
    df["Consumo_exib"] = df["Consumo_12m"] * df["Vlr Unit"]
else:
    df["DIO_calc"]     = df["DIO"]
    label_eixo        = "DIO Qtd (dias)"
    label_consumo     = "Consumo 12m (un)"
    df["Consumo_exib"] = df["Consumo_12m"]

df["Faixa_calc"]   = df["DIO_calc"].apply(categorizar_dio)
df["DIO_fmt_calc"] = df["DIO_calc"].apply(formatar_dio)

if faixas_sel:
    df = df[df["Faixa_calc"].isin(faixas_sel)]

# -------------------------------------------------
# KPIs
# -------------------------------------------------

total_itens       = len(df)
sem_consumo       = (df["Faixa_calc"] == "Sem consumo").sum()
custo_total       = df["Custo Total"].sum()
custo_sem_consumo = df[df["Faixa_calc"] == "Sem consumo"]["Custo Total"].sum()
perc_sem_consumo  = (custo_sem_consumo / custo_total * 100) if custo_total > 0 else 0

df_com_dio    = df[df["DIO_calc"] != np.inf].copy()
dio_medio     = df_com_dio["DIO_calc"].mean() if not df_com_dio.empty else 0
dio_ponderado = (
    (df_com_dio["DIO_calc"] * df_com_dio["Custo Total"]).sum()
    / df_com_dio["Custo Total"].sum()
    if df_com_dio["Custo Total"].sum() > 0 else 0
)

col1, col2, col3 = st.columns(3)
col1.markdown(f"""<div class="kpi-card"><div class="kpi-title">Total de Itens</div><div class="kpi-value">{fmt_numero(total_itens)}</div></div>""", unsafe_allow_html=True)
col2.markdown(f"""<div class="kpi-card"><div class="kpi-title">Valor em Estoque</div><div class="kpi-value">{moeda_br(custo_total)}</div></div>""", unsafe_allow_html=True)
col3.markdown(f"""<div class="kpi-card"><div class="kpi-title">Itens Sem Consumo</div><div class="kpi-value">{fmt_numero(sem_consumo)}</div></div>""", unsafe_allow_html=True)

st.markdown("")

col4, col5, col6 = st.columns(3)
col4.markdown(f"""<div class="kpi-card"><div class="kpi-title">DIO Médio ({modo})</div><div class="kpi-value">{int(round(dio_medio))} dias</div></div>""", unsafe_allow_html=True)
col5.markdown(f"""<div class="kpi-card"><div class="kpi-title">DIO Ponderado ({modo})</div><div class="kpi-value">{int(round(dio_ponderado))} dias</div></div>""", unsafe_allow_html=True)
col6.markdown(f"""<div class="kpi-card"><div class="kpi-title">Capital Imobilizado Sem Consumo</div><div class="kpi-value">{moeda_br(custo_sem_consumo)}</div><div class="kpi-title" style="color:#EC6E21;font-weight:700">{perc_sem_consumo:.1f}% do estoque total</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# FILTRO POR QTD / POR VALOR
# -------------------------------------------------

novo_modo = st.radio(
    "Calcular DIO por",
    ["Por Qtd", "Por Valor"],
    index=0 if st.session_state["modo_dio"] == "Por Qtd" else 1,
    horizontal=True,
    key="radio_modo_dio"
)

if novo_modo != st.session_state["modo_dio"]:
    st.session_state["modo_dio"] = novo_modo
    st.rerun()

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Distribuição por Faixa DIO",
    "🏆 Top 20 Maior DIO",
    "📋 Todos os Produtos",
    "🔗 Cruzamento Obsoletos",
    "📚 Base Histórica DIO"
])

with tab1:
    render_distribuicao(df, modo, moeda_br)

with tab2:
    render_top20(df, modo, label_eixo, label_consumo, moeda_br)

with tab3:
    render_todos_produtos(df, modo, label_consumo, data_selecionada, moeda_br)

with tab4:
    render_cruzamento(df, data_selecionada, empresas_sel, moeda_br)

with tab5:
    render_base_historica(df, modo, data_selecionada, moeda_br)
