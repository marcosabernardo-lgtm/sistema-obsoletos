import streamlit as st
import pandas as pd
import os

from tabs.estoque.evolucao_estoque import render as render_evolucao_estoque
from utils.navbar import render_navbar, render_filtros_topo

st.set_page_config(page_title="Dashboard Estoque", layout="wide")
render_navbar("Dashboard Evolução de Estoque")

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

# --- PROTEÇÃO E PADRONIZAÇÃO DE COLUNAS ---
if "Tipo de Estoque" not in df_hist.columns:
    df_hist["Tipo de Estoque"] = "EM ESTOQUE"
if "Conta" not in df_hist.columns:
    df_hist["Conta"] = "Outros"

df_hist["Custo Total"] = pd.to_numeric(df_hist["Custo Total"], errors="coerce").fillna(0)
df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"], errors="coerce")
df_hist = df_hist.sort_values("Data Fechamento")

# -------------------------------------------------
# CARREGAR BASE OBSOLETOS
# -------------------------------------------------
CAMINHO_OBSOLETOS_DIR = "data/obsoletos"
df_obsoleto = pd.DataFrame()

if os.path.exists(CAMINHO_OBSOLETOS_DIR):
    arquivos_obs = [f for f in os.listdir(CAMINHO_OBSOLETOS_DIR) if f.endswith(".parquet")]
    if arquivos_obs:
        try:
            df_obsoleto = pd.concat([
                pd.read_parquet(os.path.join(CAMINHO_OBSOLETOS_DIR, f))
                for f in arquivos_obs
            ], ignore_index=True)
            # Proteção para o obsoleto também
            if not df_obsoleto.empty:
                if "Tipo de Estoque" not in df_obsoleto.columns: df_obsoleto["Tipo de Estoque"] = "EM ESTOQUE"
                if "Conta" not in df_obsoleto.columns: df_obsoleto["Conta"] = "Outros"
        except Exception:
            df_obsoleto = pd.DataFrame()

# -------------------------------------------------
# FILTROS NO TOPO
# -------------------------------------------------
datas_disponiveis = sorted(df_hist["Data Fechamento"].dt.date.unique(), reverse=True)
datas_fmt_list    = [d.strftime("%d/%m/%Y") for d in datas_disponiveis]
datas_map         = {d.strftime("%d/%m/%Y"): d for d in datas_disponiveis}

data_preview_str  = st.session_state.get("estoque_data", datas_fmt_list[0])
data_preview      = pd.Timestamp(datas_map.get(data_preview_str, datas_disponiveis[0]))
df_preview        = df_hist[df_hist["Data Fechamento"] == data_preview]

empresas_disponiveis = sorted(df_preview["Empresa / Filial"].dropna().unique())

# Captura seleções atuais para filtros dependentes
ef_ja_sel     = st.session_state.get("estoque_empresa_sel", [])
filial_ja_sel = st.session_state.get("estoque_filial_sel", [])
contas_ja_sel = st.session_state.get("estoque_conta", [])

ef_ativos = [
    ef for ef in empresas_disponiveis
    if (not ef_ja_sel     or ef.split(" / ")[0].strip() in ef_ja_sel)
    and (not filial_ja_sel or ef.split(" / ")[1].strip() in filial_ja_sel)
] if (ef_ja_sel or filial_ja_sel) else list(empresas_disponiveis)

df_filtrado_opcoes = df_preview[df_preview["Empresa / Filial"].isin(ef_ativos)]

contas_disponiveis = sorted(df_filtrado_opcoes["Conta"].dropna().unique())

# Filtra opções de "Tipo de Estoque" baseada na conta selecionada (cascata)
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
    key_prefix="estoque"
)

data_selecionada = pd.Timestamp(datas_map[filtros["data"]])
empresas_sel     = filtros["empresas"]
contas_sel       = filtros.get("conta", [])
tipos_sel        = filtros.get("tipo_de_estoque", [])

# -------------------------------------------------
# FILTRAR BASE KPI E HISTÓRICO
# -------------------------------------------------
def aplicar_filtros(df_alvo):
    if df_alvo.empty: return df_alvo
    temp = df_alvo.copy()
    if empresas_sel:
        temp = temp[temp["Empresa / Filial"].isin(empresas_sel)]
    if contas_sel:
        temp = temp[temp["Conta"].isin(contas_sel)]
    if tipos_sel:
        temp = temp[temp["Tipo de Estoque"].isin(tipos_sel)]
    return temp

df_kpi = aplicar_filtros(df_hist[df_hist["Data Fechamento"] == data_selecionada])
df_hist_filtrado = aplicar_filtros(df_hist)

# -------------------------------------------------
# CALCULAR MoM e YoY
# -------------------------------------------------
datas_sorted = sorted(df_hist["Data Fechamento"].unique())
idx_atual    = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1
valor_atual  = df_kpi["Custo Total"].sum()

# Cálculo MoM
valor_mom = 0
perc_mom = 0
data_mom = None
if idx_atual > 0:
    data_mom = datas_sorted[idx_atual - 1]
    df_mom = aplicar_filtros(df_hist[df_hist["Data Fechamento"] == data_mom])
    valor_mom = df_mom["Custo Total"].sum()
    perc_mom  = ((valor_atual - valor_mom) / valor_mom * 100) if valor_mom > 0 else 0

# Cálculo YoY
valor_yoy = 0
perc_yoy = 0
data_yoy = None
data_yoy_alvo = data_selecionada - pd.DateOffset(years=1)
datas_yoy_match = [d for d in datas_sorted if abs((pd.Timestamp(d) - data_yoy_alvo).days) <= 31]
if datas_yoy_match:
    data_yoy = min(datas_yoy_match, key=lambda d: abs((pd.Timestamp(d) - data_yoy_alvo).days))
    df_yoy   = aplicar_filtros(df_hist[df_hist["Data Fechamento"] == data_yoy])
    valor_yoy = df_yoy["Custo Total"].sum()
    perc_yoy  = ((valor_atual - valor_yoy) / valor_yoy * 100) if valor_yoy > 0 else 0

# -------------------------------------------------
# CARDS KPI (TABELA)
# -------------------------------------------------
def seta(v): return "⬆" if v >= 0 else "⬇"

label_atual = data_selecionada.strftime("%y-%b").lower()
label_mom   = pd.Timestamp(data_mom).strftime("%y-%b").lower() if data_mom else "—"
label_yoy   = pd.Timestamp(data_yoy).strftime("%y-%b").lower() if data_yoy else "—"

var_mom_val = valor_atual - valor_mom if data_mom else None
var_yoy_val = valor_atual - valor_yoy if data_yoy else None

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
    bolinha = "🟢" if var_val <= 0 else "🔴"
    sinal   = "+" if var_val >= 0 else ""
    return (
        f'<tr><td style="padding:10px 16px;font-weight:{peso};font-size:{tam};color:white">{label}</td>'
        f'<td style="padding:10px 16px;font-weight:{peso};font-size:{tam};color:white;text-align:right">{moeda_br(valor)}</td>'
        f'<td style="padding:10px 16px;text-align:right;color:white;font-weight:600">{bolinha} {seta(var_val)} {sinal}{moeda_br(abs(var_val))}</td>'
        f'<td style="padding:10px 16px;text-align:right;color:white;font-weight:600">{bolinha} {seta(var_val)} {abs(var_perc):.1f}%</td></tr>'
    )

linhas = (
    linha_tabela(label_atual, valor_atual, None, None, is_header=True) +
    linha_tabela(f"MoM {label_mom}", valor_mom, var_mom_val, perc_mom) +
    linha_tabela(f"YoY {label_yoy}", valor_yoy, var_yoy_val, perc_yoy)
)

st.markdown(
    '<div class="kpi-card" style="padding:0;text-align:left;max-width:600px">' +
    '<table style="width:100%;border-collapse:collapse">' +
    '<thead style="border-bottom:1px solid rgba(255,255,255,0.08)"><tr>' +
    '<th style="font-size:10px;color:rgba(255,255,255,0.35);padding:6px 16px;text-align:left">Período</th>' +
    '<th style="font-size:10px;color:rgba(255,255,255,0.35);padding:6px 16px;text-align:right">Valor Estoque</th>' +
    '<th style="font-size:10px;color:rgba(255,255,255,0.35);padding:6px 16px;text-align:right">Variação (R$)</th>' +
    '<th style="font-size:10px;color:rgba(255,255,255,0.35);padding:6px 16px;text-align:right">Variação (%)</th>' +
    '</tr></thead><tbody>' + linhas + '</tbody></table></div>',
    unsafe_allow_html=True
)

st.markdown("---")

# -------------------------------------------------
# RENDER ABAS
# -------------------------------------------------
try:
    # Passando os dados filtrados para a tab de evolução
    render_evolucao_estoque(df_hist_filtrado, df_obsoleto, moeda_br, df_kpi, data_selecionada, valor_mom, valor_yoy)
except Exception as e:
    st.error("Erro ao renderizar o dashboard.")
    st.exception(e)