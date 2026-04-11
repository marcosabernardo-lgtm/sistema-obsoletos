import streamlit as st
import pandas as pd
import httpx
from supabase import create_client, Client, ClientOptions
from collections import defaultdict

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
# CONEXÃO SUPABASE
# -------------------------------------------------

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase() -> Client:
    http_client = httpx.Client(verify=False, timeout=60.0)
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(httpx_client=http_client))

def ler_tabela(supabase: Client, tabela: str, filtros: dict = None) -> pd.DataFrame:
    registros = []
    pagina = 0
    while True:
        query = supabase.table(tabela).select("*")
        if filtros:
            for col, val in filtros.items():
                query = query.eq(col, val)
        res = query.range(pagina * 1000, (pagina + 1) * 1000 - 1).execute()
        registros.extend(res.data)
        if len(res.data) < 1000:
            break
        pagina += 1
    return pd.DataFrame(registros)

# -------------------------------------------------
# NORMALIZA EMPRESA
# -------------------------------------------------

def normalizar_empresa(nome):
    nome = str(nome).upper()
    if "TOOLS" in nome:    return "Tools"
    if "MAQUINAS" in nome: return "Maquinas"
    if "ALLSERVICE" in nome or "SERVICE" in nome: return "Service"
    if "ROBOTICA" in nome: return "Robotica"
    return nome

EMPRESA_FILIAL_MAP_NORM = {
    ("TOOLS",    "00"): "Tools / Matriz",
    ("TOOLS",    "01"): "Tools / Filial",
    ("MAQUINAS", "00"): "Maquinas / Matriz",
    ("MAQUINAS", "01"): "Maquinas / Filial",
    ("MAQUINAS", "02"): "Maquinas / Jundiai",
    ("ROBOTICA", "00"): "Robotica / Matriz",
    ("ROBOTICA", "01"): "Robotica / Filial Jaragua",
    ("SERVICE",  "01"): "Service / Matriz",
    ("SERVICE",  "02"): "Service / Filial",
    ("SERVICE",  "03"): "Service / Caxias",
    ("SERVICE",  "04"): "Service / Jundiai",
}

def mapear_empresa_filial_norm(empresa: str, filial: str) -> str:
    key = (str(empresa).strip().upper(), str(filial).strip().zfill(2))
    return EMPRESA_FILIAL_MAP_NORM.get(key, f"{empresa} / {filial}")
    ("ALLTECH TOOLS DO BRASIL LTDA",         "MATRIZ"):         "Tools / Matriz",
    ("ALLTECH TOOLS DO BRASIL LTDA",         "FILIAL"):         "Tools / Filial",
    ("ALLTECH MAQUINAS E EQUIPAMENTOS LTDA", "MATRIZ"):         "Maquinas / Matriz",
    ("ALLTECH MAQUINAS E EQUIPAMENTOS LTDA", "FILIAL"):         "Maquinas / Filial",
    ("ALLTECH MAQUINAS E EQUIPAMENTOS LTDA", "JUNDIAI"):        "Maquinas / Jundiai",
    ("ALLTECH ROBOTICA E AUTOMACAO LTDA",    "MATRIZ"):         "Robotica / Matriz",
    ("ALLTECH ROBOTICA E AUTOMACAO LTDA",    "FILIAL JARAGUA"): "Robotica / Filial Jaragua",
    ("ALLSERVICE MANUTENCAO",                "MATRIZ"):         "Service / Matriz",
    ("ALLSERVICE MANUTENCAO",                "FILIAL"):         "Service / Filial",
    ("ALLSERVICE MANUTENCAO",                "CAXIAS"):         "Service / Caxias",
    ("ALLSERVICE MANUTENCAO LTDA",           "JUNDIAI"):        "Service / Jundiai",
}

def mapear_empresa_filial(empresa: str, filial: str) -> str:
    key = (str(empresa).strip().upper(), str(filial).strip().upper())
    return EMPRESA_FILIAL_MAP.get(key, f"{empresa} / {filial}")

# -------------------------------------------------
# CARREGAR BASE HISTÓRICA DO SUPABASE
# -------------------------------------------------

@st.cache_data(ttl=3600)
def carregar_historico():
    supabase = get_supabase()

    # Estoque histórico completo
    df = ler_tabela(supabase, "estoque_fechamentos")

    # Usadas
    df_usadas = ler_tabela(supabase, "estoque_usadas")
    usadas_tipo_por_empresa = defaultdict(dict)
    for _, row in df_usadas.iterrows():
        empresa = str(row.get("empresa", "")).strip()
        tipo    = str(row.get("tipo", "Maquina Usada")).strip().title()
        codigo  = str(row.get("codigo", "")).strip().replace(".0", "")
        usadas_tipo_por_empresa[empresa][codigo] = tipo

    # Renomear colunas
    df = df.rename(columns={
        "data_fechamento": "Data Fechamento",
        "empresa":         "Empresa",
        "filial":          "Filial",
        "tipo_de_estoque": "Tipo de Estoque",
        "conta":           "Conta",
        "produto":         "Produto",
        "descricao":       "Descricao",
        "unid":            "Unid",
        "saldo_atual":     "Saldo Atual",
        "vlr_unit":        "Vlr Unit",
        "custo_total":     "Custo Total",
    })

    # Tipo de Estoque
    df["Tipo de Estoque"] = df["Tipo de Estoque"].fillna("Em Estoque").astype(str).str.strip().str.title()

    # Empresa / Filial via mapeamento normalizado
    df["Empresa / Filial"] = df.apply(
        lambda r: mapear_empresa_filial_norm(r["Empresa"], r["Filial"]), axis=1
    )
    df = df.drop(columns=["Empresa", "Filial"], errors="ignore")

    # Produto
    df["Produto"] = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)

    # Numéricos
    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)
    df["Vlr Unit"]    = pd.to_numeric(df["Vlr Unit"],    errors="coerce").fillna(0)
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"], errors="coerce")

    # Conta
    if "Conta" in df.columns:
        df["Conta"] = df["Conta"].astype(str).str.strip().str.title()

    # Marcar usadas
    for empresa, tipo_map in usadas_tipo_por_empresa.items():
        for codigo, tipo in tipo_map.items():
            mask = (
                df["Empresa / Filial"].str.startswith(empresa) &
                (df["Produto"] == codigo)
            )
            df.loc[mask, "Conta"] = tipo

    if "Tipo de Estoque" not in df.columns:
        df["Tipo de Estoque"] = "Em Estoque"
    if "Conta" not in df.columns:
        df["Conta"] = "Outros"

    return df.sort_values("Data Fechamento")

# -------------------------------------------------
# CARREGAR BASE OBSOLETOS (último fechamento)
# -------------------------------------------------

@st.cache_data(ttl=3600)
def carregar_obsoletos():
    try:
        from motor.motor_obsoletos import executar_motor
        df_obs, _ = executar_motor()
        return df_obs
    except Exception:
        return pd.DataFrame()

# -------------------------------------------------
# CARREGAMENTO
# -------------------------------------------------

with st.spinner("Carregando dados do Supabase..."):
    try:
        df_hist = carregar_historico()
    except Exception as e:
        st.error("Erro ao carregar dados do Supabase.")
        st.exception(e)
        st.stop()

if df_hist.empty:
    st.warning("⚠️ Base de dados vazia.")
    st.stop()

df_obsoleto = carregar_obsoletos()

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

df_kpi           = aplicar_filtros(df_hist[df_hist["Data Fechamento"] == data_selecionada])
df_hist_filtrado = aplicar_filtros(df_hist)

# -------------------------------------------------
# CALCULAR MoM e YoY
# -------------------------------------------------

datas_sorted = sorted(df_hist["Data Fechamento"].unique())
idx_atual    = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1
valor_atual  = df_kpi["Custo Total"].sum()

valor_mom = 0; perc_mom = 0; data_mom = None
if idx_atual > 0:
    data_mom  = datas_sorted[idx_atual - 1]
    df_mom    = aplicar_filtros(df_hist[df_hist["Data Fechamento"] == data_mom])
    valor_mom = df_mom["Custo Total"].sum()
    perc_mom  = ((valor_atual - valor_mom) / valor_mom * 100) if valor_mom > 0 else 0

valor_yoy = 0; perc_yoy = 0; data_yoy = None
data_yoy_alvo   = data_selecionada - pd.DateOffset(years=1)
datas_yoy_match = [d for d in datas_sorted if abs((pd.Timestamp(d) - data_yoy_alvo).days) <= 31]
if datas_yoy_match:
    data_yoy  = min(datas_yoy_match, key=lambda d: abs((pd.Timestamp(d) - data_yoy_alvo).days))
    df_yoy    = aplicar_filtros(df_hist[df_hist["Data Fechamento"] == data_yoy])
    valor_yoy = df_yoy["Custo Total"].sum()
    perc_yoy  = ((valor_atual - valor_yoy) / valor_yoy * 100) if valor_yoy > 0 else 0

# -------------------------------------------------
# CARDS KPI
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
    render_evolucao_estoque(df_hist_filtrado, df_obsoleto, moeda_br, df_kpi, data_selecionada, valor_mom, valor_yoy)
except Exception as e:
    st.error("Erro ao renderizar o dashboard.")
    st.exception(e)