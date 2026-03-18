import streamlit as st
import pandas as pd
import os

from tabs.estoque.evolucao_estoque import render as render_evolucao_estoque
from utils.navbar import render_navbar, render_filtros_topo

st.set_page_config(page_title="Dashboard Estoque", layout="wide")
render_navbar("Dashboard Evolução de Estoque")

# -------------------------------------------------
# CSS
# -------------------------------------------------
st.markdown("""
<style>
/* Esconde sidebar completamente neste dashboard */
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
    min-height:110px;
    display:flex;
    flex-direction:column;
    justify-content:center;
}
.kpi-title{ font-size:13px; color:#ccc; }
.kpi-value{ font-size:24px; font-weight:700; color:white; }
.kpi-sub{ font-size:13px; color:#aaa; margin-top:4px; }
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
# CARREGAR BASE HISTÓRICA
# -------------------------------------------------
CAMINHO_BASE = "data/estoque/estoque_historico.parquet"

if not os.path.exists(CAMINHO_BASE):
    st.warning("⚠️ Nenhuma base de dados encontrada. Acesse o **Configurador** para processar os dados.")
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
# CARREGAR BASE OBSOLETOS
# -------------------------------------------------
CAMINHO_OBSOLETOS_DIR = "data/obsoletos"

if os.path.exists(CAMINHO_OBSOLETOS_DIR):
    arquivos_obs = [f for f in os.listdir(CAMINHO_OBSOLETOS_DIR) if f.endswith(".parquet")]
    if arquivos_obs:
        try:
            df_obsoleto = pd.concat([
                pd.read_parquet(os.path.join(CAMINHO_OBSOLETOS_DIR, f))
                for f in arquivos_obs
            ], ignore_index=True)
        except Exception:
            df_obsoleto = pd.DataFrame()
    else:
        df_obsoleto = pd.DataFrame()
else:
    df_obsoleto = pd.DataFrame()

# -------------------------------------------------
# FILTROS NO TOPO — bidirecional
# -------------------------------------------------
datas_disponiveis = sorted(df_hist["Data Fechamento"].dt.date.unique(), reverse=True)
datas_fmt_list = [d.strftime("%d/%m/%Y") for d in datas_disponiveis]
datas_map = {d.strftime("%d/%m/%Y"): d for d in datas_disponiveis}

# Base do fechamento selecionado (usa session_state para saber data atual)
data_preview_str = st.session_state.get("estoque_data", datas_fmt_list[0])
data_preview = pd.Timestamp(datas_map.get(data_preview_str, datas_disponiveis[0]))
df_preview = df_hist[df_hist["Data Fechamento"] == data_preview]

# Filtros bidirecionais — cada um filtra o outro
empresas_ja_sel = st.session_state.get("estoque_empresas", [])
contas_ja_sel   = st.session_state.get("estoque_conta", [])

# Empresa: filtrada pelas contas já selecionadas
df_emp_filtro = df_preview.copy()
if contas_ja_sel:
    df_emp_filtro = df_emp_filtro[df_emp_filtro["Conta"].isin(contas_ja_sel)]
empresas_disponiveis = sorted(df_emp_filtro["Empresa / Filial"].dropna().unique()) if "Empresa / Filial" in df_emp_filtro.columns else []

# Conta: filtrada pelas empresas já selecionadas
df_conta_filtro = df_preview.copy()
if empresas_ja_sel:
    df_conta_filtro = df_conta_filtro[df_conta_filtro["Empresa / Filial"].isin(empresas_ja_sel)]
contas_disponiveis = sorted(df_conta_filtro["Conta"].dropna().unique()) if "Conta" in df_conta_filtro.columns else []

filtros = render_filtros_topo(
    datas=datas_fmt_list,
    empresas=empresas_disponiveis,
    extras={"Conta": contas_disponiveis} if contas_disponiveis else None,
    key_prefix="estoque"
)

data_selecionada = pd.Timestamp(datas_map[filtros["data"]])
empresas_sel     = filtros["empresas"]
contas_sel       = filtros.get("conta", [])

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

col1, col2 = st.columns(2)

# Card 1 — Valor atual + variações MoM e YoY
mom_linha = f'<div class="kpi-sub" style="color:{cor_perc(perc_mom)};font-size:13px">{seta(perc_mom)} {abs(perc_mom):.1f}% vs mês anterior ({pd.Timestamp(data_mom).strftime("%y-%b").lower()})</div>' if valor_mom is not None else ""
yoy_linha = f'<div class="kpi-sub" style="color:{cor_perc(perc_yoy)};font-size:13px">{seta(perc_yoy)} {abs(perc_yoy):.1f}% vs ano anterior ({pd.Timestamp(data_yoy).strftime("%y-%b").lower()})</div>' if valor_yoy is not None else ""

col1.markdown(f'<div class="kpi-card"><div class="kpi-title">Valor Estoque {data_selecionada.strftime("%y-%b").lower()}</div><div class="kpi-value">{moeda_br(valor_atual)}</div>{mom_linha}{yoy_linha}</div>', unsafe_allow_html=True)

# Card 2 — MoM e YoY juntos
mom_label = pd.Timestamp(data_mom).strftime('%y-%b').lower() if valor_mom is not None else ""
yoy_label = pd.Timestamp(data_yoy).strftime('%y-%b').lower() if valor_yoy is not None else ""
mom_val = moeda_br(valor_mom) if valor_mom is not None else "—"
yoy_val = moeda_br(valor_yoy) if valor_yoy is not None else "—"

col2.markdown(
    f'<div class="kpi-card" style="display:flex;flex-direction:row;gap:0;padding:0;">'
    f'<div style="flex:1;padding:16px;border-right:1px solid rgba(255,255,255,0.1);text-align:center;">'
    f'<div class="kpi-title">MoM {mom_label}</div><div class="kpi-value">{mom_val}</div></div>'
    f'<div style="flex:1;padding:16px;text-align:center;">'
    f'<div class="kpi-title">YoY {yoy_label}</div><div class="kpi-value">{yoy_val}</div></div>'
    f'</div>',
    unsafe_allow_html=True
)

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
    render_evolucao_estoque(df_hist_filtrado, df_obsoleto, moeda_br, df_kpi, data_selecionada, valor_mom, valor_yoy)
except Exception as e:
    st.error("Erro ao renderizar o dashboard.")
    st.exception(e)
