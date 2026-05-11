import time
import streamlit as st
import pandas as pd
from supabase import create_client, Client

from utils.navbar import render_navbar

st.set_page_config(page_title="Máquinas Usadas", layout="wide")
render_navbar("Máquinas Usadas")

st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }
.kpi-card {
    background-color: #005562;
    border: 2px solid #EC6E21;
    padding: 16px;
    border-radius: 10px;
    text-align: center;
    min-height: 100px;
    display: flex; flex-direction: column; justify-content: center;
}
.kpi-title { font-size: 13px; color: #ccc; }
.kpi-value { font-size: 26px; font-weight: 700; color: white; }
.kpi-sub   { font-size: 12px; color: #aaa; margin-top: 4px; }
div[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stDataFrame"] thead th {
    background-color: #0f5a60 !important;
    color: white !important;
    font-weight: 600 !important;
    border-bottom: 1px solid #EC6E21 !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🔧 Máquinas Usadas")
st.markdown("Gestão e histórico das máquinas classificadas como Usada ou Nova.")
st.markdown("---")

# -------------------------------------------------
# CONEXÃO
# -------------------------------------------------

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def _executar_com_retry(fn, tentativas=3, espera=2):
    for i in range(tentativas):
        try:
            return fn()
        except Exception as e:
            if i < tentativas - 1:
                time.sleep(espera)
            else:
                raise

supabase = get_supabase()

def moeda(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# -------------------------------------------------
# CARGA DE DADOS
# -------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def carregar_usadas() -> pd.DataFrame:
    resp = _executar_com_retry(
        lambda: supabase.table("estoque_usadas")
            .select("id, empresa, codigo, tipo, descricao")
            .order("empresa")
            .execute()
    )
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame(
        columns=["id", "empresa", "codigo", "tipo", "descricao"]
    )

@st.cache_data(ttl=120, show_spinner=False)
def carregar_historico(codigos: tuple, empresas: tuple) -> pd.DataFrame:
    if not codigos:
        return pd.DataFrame()
    resp = _executar_com_retry(
        lambda: supabase.table("estoque_fechamentos")
            .select("data_fechamento,empresa,filial,produto,descricao,unid,saldo_atual,vlr_unit,custo_total")
            .in_("produto", list(codigos))
            .order("data_fechamento")
            .execute()
    )
    df = pd.DataFrame(resp.data) if resp.data else pd.DataFrame()
    if df.empty:
        return df
    def _norm(e):
        e = str(e).upper()
        if "TOOLS" in e:      return "Tools"
        if "MAQUINAS" in e:   return "Maquinas"
        if "ALLSERVICE" in e: return "Service"
        if "ROBOTICA" in e:   return "Robotica"
        return e
    df["empresa_norm"] = df["empresa"].apply(_norm)
    mask = pd.Series(False, index=df.index)
    for cod, emp in zip(codigos, empresas):
        mask |= (df["produto"] == cod) & (df["empresa_norm"] == emp)
    return df[mask].copy()

# -------------------------------------------------
# CARREGA DADOS
# -------------------------------------------------

try:
    df_usadas = carregar_usadas()
    erro_carga = None
except Exception as e:
    df_usadas = pd.DataFrame(columns=["id", "empresa", "codigo", "tipo", "descricao"])
    erro_carga = str(e)

if erro_carga:
    st.error(f"Erro ao conectar ao banco: {erro_carga}")
    st.stop()

# -------------------------------------------------
# KPIs
# -------------------------------------------------

if not df_usadas.empty:
    codigos_tuple = tuple(df_usadas["codigo"].tolist())
    empresas_tuple = tuple(df_usadas["empresa"].tolist())
    try:
        df_hist = carregar_historico(codigos_tuple, empresas_tuple)
    except Exception:
        df_hist = pd.DataFrame()
else:
    df_hist = pd.DataFrame()

total_cadastradas = len(df_usadas)
total_usadas  = (df_usadas["tipo"] == "Maquina Usada").sum() if not df_usadas.empty else 0
total_novas   = (df_usadas["tipo"] == "Máquina Nova").sum()  if not df_usadas.empty else 0

if not df_hist.empty:
    ultimo_fechamento = df_hist["data_fechamento"].max()
    df_ultimo = df_hist[df_hist["data_fechamento"] == ultimo_fechamento]
    valor_total = df_ultimo["custo_total"].sum()
    qtd_total   = df_ultimo["saldo_atual"].sum()
else:
    ultimo_fechamento = "—"
    valor_total = None
    qtd_total   = None

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-title">Total Cadastradas</div>
        <div class="kpi-value">{total_cadastradas}</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-title">Usadas / Novas</div>
        <div class="kpi-value">{total_usadas} / {total_novas}</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-title">Valor em Estoque</div>
        <div class="kpi-value">{moeda(valor_total) if valor_total else "—"}</div>
        <div class="kpi-sub">Último fechamento: {ultimo_fechamento}</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-title">Unidades em Estoque</div>
        <div class="kpi-value">{f"{qtd_total:,.0f}" if qtd_total else "—"}</div>
        <div class="kpi-sub">Último fechamento: {ultimo_fechamento}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

aba_cadastro, aba_historico = st.tabs(["📋 Cadastro", "📈 Histórico"])

# ── ABA CADASTRO ─────────────────────────────────

with aba_cadastro:
    if not df_usadas.empty:
        st.dataframe(
            df_usadas[["empresa", "codigo", "tipo", "descricao"]].rename(columns={
                "empresa":   "Empresa",
                "codigo":    "Código",
                "tipo":      "Tipo",
                "descricao": "Descrição",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nenhuma máquina cadastrada.")

    st.markdown("---")

    EMPRESAS_OPCOES = ["Tools", "Maquinas", "Robotica", "Service"]
    TIPOS_OPCOES    = ["Maquina Usada", "Máquina Nova"]

    col_add, col_rem = st.columns(2)

    with col_add:
        st.subheader("➕ Adicionar")
        with st.form("form_adicionar", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nova_empresa = st.selectbox("Empresa", EMPRESAS_OPCOES)
                novo_codigo  = st.text_input("Código do Produto")
            with c2:
                novo_tipo = st.selectbox("Tipo", TIPOS_OPCOES)
                nova_desc = st.text_input("Descrição (opcional)")
            submitted = st.form_submit_button("➕ Adicionar", type="primary", use_container_width=True)
            if submitted:
                if not novo_codigo.strip():
                    st.error("Informe o código do produto.")
                else:
                    try:
                        supabase.table("estoque_usadas").insert({
                            "empresa":   nova_empresa,
                            "codigo":    novo_codigo.strip(),
                            "tipo":      novo_tipo,
                            "descricao": nova_desc.strip() or None,
                        }).execute()
                        st.success(f"✅ {novo_codigo.strip()} adicionado como {novo_tipo}.")
                        carregar_usadas.clear()
                        carregar_historico.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao adicionar: {e}")

    with col_rem:
        st.subheader("🗑️ Remover")
        if not df_usadas.empty:
            opcoes = [
                f"{r['empresa']} | {r['codigo']} | {r['tipo']}"
                for _, r in df_usadas.iterrows()
            ]
            sel = st.selectbox("Selecione para remover", opcoes)
            if st.button("🗑️ Remover", type="secondary", use_container_width=True):
                idx = opcoes.index(sel)
                id_remover = df_usadas.iloc[idx]["id"]
                try:
                    supabase.table("estoque_usadas").delete().eq("id", id_remover).execute()
                    st.success("✅ Removido com sucesso.")
                    carregar_usadas.clear()
                    carregar_historico.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao remover: {e}")
        else:
            st.info("Nenhuma máquina para remover.")

# ── ABA HISTÓRICO ─────────────────────────────────

with aba_historico:
    if df_hist.empty:
        st.info("Nenhum histórico encontrado. Verifique se há fechamentos importados para as máquinas cadastradas.")
    else:
        df_hist["data_fechamento"] = pd.to_datetime(df_hist["data_fechamento"])

        # Filtros
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            empresas_disp = sorted(df_hist["empresa_norm"].dropna().unique())
            sel_empresas = st.multiselect("Empresa", empresas_disp, default=empresas_disp)
        with col_f2:
            codigos_disp = sorted(df_hist["produto"].dropna().unique())
            sel_codigos = st.multiselect("Código", codigos_disp, default=codigos_disp)
        with col_f3:
            datas_disp = sorted(df_hist["data_fechamento"].dt.strftime("%Y-%m-%d").unique())
            sel_datas = st.multiselect("Fechamento", datas_disp, default=datas_disp)

        df_filtrado = df_hist[
            df_hist["empresa_norm"].isin(sel_empresas) &
            df_hist["produto"].isin(sel_codigos) &
            df_hist["data_fechamento"].dt.strftime("%Y-%m-%d").isin(sel_datas)
        ].copy()

        if df_filtrado.empty:
            st.warning("Nenhum dado para os filtros selecionados.")
        else:
            # Evolução do custo total por fechamento
            st.subheader("Evolução do Valor em Estoque")
            df_evolucao = (
                df_filtrado.groupby("data_fechamento")["custo_total"]
                .sum()
                .reset_index()
                .sort_values("data_fechamento")
            )
            st.line_chart(df_evolucao.set_index("data_fechamento")["custo_total"])

            # Tabela detalhada
            st.subheader("Detalhe por Fechamento")
            df_exib = df_filtrado[[
                "data_fechamento", "empresa_norm", "produto", "descricao",
                "unid", "saldo_atual", "vlr_unit", "custo_total"
            ]].rename(columns={
                "data_fechamento": "Fechamento",
                "empresa_norm":    "Empresa",
                "produto":         "Código",
                "descricao":       "Descrição",
                "unid":            "Unid",
                "saldo_atual":     "Saldo",
                "vlr_unit":        "Vlr Unit",
                "custo_total":     "Custo Total",
            }).sort_values(["Fechamento", "Empresa", "Código"], ascending=[False, True, True])

            df_exib["Fechamento"] = df_exib["Fechamento"].dt.strftime("%d/%m/%Y")

            st.dataframe(df_exib, use_container_width=True, hide_index=True)

            # Pivot: custo total por máquina × fechamento
            st.subheader("Custo Total por Máquina e Fechamento")
            try:
                df_pivot = df_filtrado.pivot_table(
                    index=["empresa_norm", "produto", "descricao"],
                    columns="data_fechamento",
                    values="custo_total",
                    aggfunc="sum",
                )
                df_pivot.columns = [c.strftime("%m/%Y") for c in df_pivot.columns]
                df_pivot.index.names = ["Empresa", "Código", "Descrição"]
                st.dataframe(df_pivot.style.format(lambda v: moeda(v) if pd.notna(v) else "—"),
                             use_container_width=True)
            except Exception:
                pass
