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

# Lista completa de EF para o navbar (split feito internamente)
empresas_disponiveis = sorted(df_preview["Empresa / Filial"].dropna().unique()) if "Empresa / Filial" in df_preview.columns else []

# Conta: filtrada pelos EF ativos (Empresa + Filial já selecionados)
ef_ja_sel     = st.session_state.get("estoque_empresa_sel", [])
filial_ja_sel = st.session_state.get("estoque_filial_sel", [])
contas_ja_sel = st.session_state.get("estoque_conta", [])

ef_ativos = [
    ef for ef in empresas_disponiveis
    if (not ef_ja_sel     or ef.split(" / ")[0].strip() in ef_ja_sel)
    and (not filial_ja_sel or ef.split(" / ")[1].strip() in filial_ja_sel)
] if (ef_ja_sel or filial_ja_sel) else list(empresas_disponiveis)

df_conta_filtro = df_preview[df_preview["Empresa / Filial"].isin(ef_ativos)]
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
# CARDS KPI — tabela única
# -------------------------------------------------
def seta(v):
    return "⬆" if v >= 0 else "⬇"

def cor_var(v):
    return "#EC6E21" if v >= 0 else "#51cf66"

label_atual = data_selecionada.strftime("%y-%b").lower()
label_mom   = pd.Timestamp(data_mom).strftime("%y-%b").lower() if valor_mom is not None else "—"
label_yoy   = pd.Timestamp(data_yoy).strftime("%y-%b").lower() if valor_yoy is not None else "—"

var_mom_val = valor_atual - valor_mom if valor_mom is not None else None
var_yoy_val = valor_atual - valor_yoy if valor_yoy is not None else None

def linha_tabela(label, valor, var_val, var_perc, is_header=False):
    peso = "700" if is_header else "400"
    tam  = "16px" if is_header else "14px"
    if var_val is None:
        return (
            f'<tr><td style="padding:10px 16px;font-weight:{peso};font-size:{tam};color:white">{label}</td>'
            f'<td style="padding:10px 16px;font-weight:{peso};font-size:{tam};color:white;text-align:right">{moeda_br(valor)}</td>'
            f'<td style="padding:10px 16px;text-align:right;color:rgba(255,255,255,0.3)">—</td>'
            f'<td style="padding:10px 16px;text-align:right;color:rgba(255,255,255,0.3)">—</td></tr>'
        )
    bolinha = "🟢" if var_val < 0 else "🔴"
    sinal = "+" if var_val >= 0 else "-"
    return (
        f'<tr><td style="padding:10px 16px;font-weight:{peso};font-size:{tam};color:white">{label}</td>'
        f'<td style="padding:10px 16px;font-weight:{peso};font-size:{tam};color:white;text-align:right">{moeda_br(valor)}</td>'
        f'<td style="padding:10px 16px;text-align:right;color:white;font-weight:600">{bolinha} {seta(var_val)} {sinal}{moeda_br(abs(var_val))}</td>'
        f'<td style="padding:10px 16px;text-align:right;color:white;font-weight:600">{bolinha} {seta(var_val)} {abs(var_perc):.1f}%</td></tr>'
    )

linhas = (
    linha_tabela(label_atual, valor_atual, None, None, is_header=True) +
    linha_tabela(f"MoM {label_mom}", valor_mom if valor_mom else 0, var_mom_val, perc_mom if perc_mom else 0) +
    linha_tabela(f"YoY {label_yoy}", valor_yoy if valor_yoy else 0, var_yoy_val, perc_yoy if perc_yoy else 0)
)

st.markdown(
    "<style>.tb-kpi{width:100%;border-collapse:collapse}"
    ".tb-kpi th{font-size:10px;font-weight:600;letter-spacing:2px;text-transform:uppercase;"
    "color:rgba(255,255,255,0.35);padding:6px 16px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.08)}"
    ".tb-kpi th:not(:first-child){text-align:right}"
    ".tb-kpi tr{border-bottom:1px solid rgba(255,255,255,0.06)}"
    ".tb-kpi tr:last-child{border-bottom:none}</style>"
    '<div class="kpi-card" style="padding:0;text-align:left;max-width:600px">' +
    '<table class="tb-kpi"><thead><tr>' +
    '<th>Período</th><th>Valor Estoque</th><th>Variação (R$)</th><th>Variação (%)</th>' +
    '</tr></thead><tbody>' + linhas + '</tbody></table></div>',
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
