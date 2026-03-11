import streamlit as st
import pandas as pd
import os

from tabs.estoque.evolucao_estoque import render as render_evolucao_estoque

st.set_page_config(page_title="Dashboard Estoque", layout="wide")

# -------------------------------------------------
# CSS
# -------------------------------------------------
st.markdown("""
<style>
section[data-testid="stSidebar"]{
    width:260px !important;
}
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
.kpi-title{ font-size:13px; color:#ccc; }
.kpi-value{ font-size:24px; font-weight:700; color:white; }
.kpi-sub{ font-size:16px; color:#aaa; margin-top:6px; }
</style>
""", unsafe_allow_html=True)

st.title("📦 Dashboard Evolução de Estoque")
st.markdown("---")

# -------------------------------------------------
# MOEDA
# -------------------------------------------------
def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def moeda_br_curta(valor):
    if abs(valor) >= 1_000_000:
        return f"R$ {valor/1_000_000:.1f} Mi"
    if abs(valor) >= 1_000:
        return f"R$ {valor/1_000:.1f} Mil"
    return moeda_br(valor)

# -------------------------------------------------
# CARREGAR BASE
# -------------------------------------------------
CAMINHO_BASE = "data/estoque/estoque_historico.parquet"

if not os.path.exists(CAMINHO_BASE):
    st.warning("⚠️ Nenhuma base de dados encontrada. Acesse a página **app** para fazer o upload.")
    st.stop()

try:
    df_hist = pd.read_parquet(CAMINHO_BASE)
except Exception as e:
    st.error("Erro ao carregar a base de estoque.")
    st.exception(e)
    st.stop()

if df_hist.empty:
    st.warning("⚠️ Base de dados vazia.")
    st.stop()

df_hist["Custo Total"] = pd.to_numeric(df_hist["Custo Total"], errors="coerce").fillna(0)
df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"], errors="coerce")
df_hist = df_hist.sort_values("Data Fechamento")

# -------------------------------------------------
# SIDEBAR — FILTROS
# -------------------------------------------------
st.sidebar.header("Filtros")

datas_disponiveis = sorted(df_hist["Data Fechamento"].dt.date.unique(), reverse=True)
datas_fmt = {d.strftime("%d/%m/%Y"): d for d in datas_disponiveis}

data_sel = st.sidebar.selectbox(
    "Data de Fechamento",
    options=list(datas_fmt.keys()),
    index=0
)
data_selecionada = pd.Timestamp(datas_fmt[data_sel])

empresas_sel = st.sidebar.multiselect(
    "Empresa / Filial",
    sorted(df_hist["Empresa / Filial"].dropna().unique()) if "Empresa / Filial" in df_hist.columns else []
)

contas_sel = st.sidebar.multiselect(
    "Conta",
    sorted(df_hist["Conta"].dropna().unique()) if "Conta" in df_hist.columns else []
)

# -------------------------------------------------
# FILTRAR BASE KPI
# -------------------------------------------------
df_kpi = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()

if empresas_sel:
    df_kpi = df_kpi[df_kpi["Empresa / Filial"].isin(empresas_sel)]
if contas_sel:
    df_kpi = df_kpi[df_kpi["Conta"].isin(contas_sel)]

# -------------------------------------------------
# CALCULAR MoM e YoY
# -------------------------------------------------
datas_sorted = sorted(df_hist["Data Fechamento"].unique())
idx_atual = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1

valor_atual = df_kpi["Custo Total"].sum()

# MoM — mês anterior
if idx_atual > 0:
    data_mom = datas_sorted[idx_atual - 1]
    df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()
    if empresas_sel:
        df_mom = df_mom[df_mom["Empresa / Filial"].isin(empresas_sel)]
    if contas_sel:
        df_mom = df_mom[df_mom["Conta"].isin(contas_sel)]
    valor_mom = df_mom["Custo Total"].sum()
    perc_mom = ((valor_atual - valor_mom) / valor_mom * 100) if valor_mom > 0 else 0
else:
    valor_mom = None
    perc_mom = None

# YoY — mesmo mês ano anterior
data_yoy_alvo = data_selecionada - pd.DateOffset(years=1)
datas_yoy = [d for d in datas_sorted if abs((pd.Timestamp(d) - data_yoy_alvo).days) <= 31]
if datas_yoy:
    data_yoy = min(datas_yoy, key=lambda d: abs((pd.Timestamp(d) - data_yoy_alvo).days))
    df_yoy = df_hist[df_hist["Data Fechamento"] == data_yoy].copy()
    if empresas_sel:
        df_yoy = df_yoy[df_yoy["Empresa / Filial"].isin(empresas_sel)]
    if contas_sel:
        df_yoy = df_yoy[df_yoy["Conta"].isin(contas_sel)]
    valor_yoy = df_yoy["Custo Total"].sum()
    perc_yoy = ((valor_atual - valor_yoy) / valor_yoy * 100) if valor_yoy > 0 else 0
else:
    valor_yoy = None
    perc_yoy = None

# -------------------------------------------------
# CARDS KPI
# -------------------------------------------------
def seta(v):
    return "⬆" if v >= 0 else "⬇"

def cor_perc(v):
    return "#ff6b6b" if v >= 0 else "#51cf66"

col1, col2, col3 = st.columns(3)

col1.markdown(f"""
<div class="kpi-card">
    <div class="kpi-title">Valor Estoque {data_selecionada.strftime('%y-%b').lower()}</div>
    <div class="kpi-value">{moeda_br(valor_atual)}</div>
    <div class="kpi-sub">&nbsp;</div>
</div>
""", unsafe_allow_html=True)

if valor_mom is not None:
    sub_mom = f'<div class="kpi-sub" style="color:{cor_perc(perc_mom)}">{seta(perc_mom)} {abs(perc_mom):.1f}% vs mês anterior</div>'
    col2.markdown(f"""
<div class="kpi-card">
    <div class="kpi-title">Valor Estoque MoM {pd.Timestamp(data_mom).strftime('%y-%b').lower()}</div>
    <div class="kpi-value">{moeda_br(valor_mom)}</div>
    {sub_mom}
</div>
""", unsafe_allow_html=True)
else:
    col2.markdown('<div class="kpi-card"><div class="kpi-title">MoM</div><div class="kpi-value">—</div></div>', unsafe_allow_html=True)

if valor_yoy is not None:
    sub_yoy = f'<div class="kpi-sub" style="color:{cor_perc(perc_yoy)}">{seta(perc_yoy)} {abs(perc_yoy):.1f}% vs ano anterior</div>'
    col3.markdown(f"""
<div class="kpi-card">
    <div class="kpi-title">Valor Estoque YoY {pd.Timestamp(data_yoy).strftime('%y-%b').lower()}</div>
    <div class="kpi-value">{moeda_br(valor_yoy)}</div>
    {sub_yoy}
</div>
""", unsafe_allow_html=True)
else:
    col3.markdown('<div class="kpi-card"><div class="kpi-title">YoY</div><div class="kpi-value">—</div></div>', unsafe_allow_html=True)

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
# RENDER ABAS
# -------------------------------------------------
try:
    render_evolucao_estoque(df_hist_filtrado, moeda_br, df_kpi, data_selecionada, valor_mom, valor_yoy)
except Exception as e:
    st.error("Erro ao renderizar o dashboard.")
    st.exception(e)