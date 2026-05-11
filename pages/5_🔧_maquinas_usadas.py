import re
import streamlit as st
import pandas as pd
import pg8000.native as pg8000

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
# CONEXÃO DIRETA POSTGRESQL
# -------------------------------------------------

def _nova_conn():
    db_url = st.secrets["SUPABASE_DB"]
    m = re.match(r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url)
    return pg8000.Connection(
        user=m[1], password=m[2], host=m[3],
        port=int(m[4]), database=m[5], ssl_context=True
    )

def db_query(sql: str, params=None) -> list[dict]:
    conn = _nova_conn()
    try:
        rows = conn.run(sql, **(params or {}))
        cols = [c["name"] for c in conn.columns]
        return [dict(zip(cols, row)) for row in rows]
    finally:
        try:
            conn.close()
        except Exception:
            pass

def db_exec(sql: str, params=None):
    conn = _nova_conn()
    try:
        conn.run(sql, **(params or {}))
    finally:
        try:
            conn.close()
        except Exception:
            pass

def moeda(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# -------------------------------------------------
# CARGA DE DADOS
# -------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def carregar_usadas() -> pd.DataFrame:
    rows = db_query("""
        SELECT id, empresa, codigo, tipo, descricao
        FROM estoque_usadas
        ORDER BY empresa, codigo
    """)
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["id", "empresa", "codigo", "tipo", "descricao"]
    )

@st.cache_data(ttl=120, show_spinner=False)
def carregar_historico(codigos: tuple) -> pd.DataFrame:
    if not codigos:
        return pd.DataFrame()
    placeholders = ", ".join(f":{i}" for i in range(len(codigos)))
    params = {str(i): cod for i, cod in enumerate(codigos)}
    rows = db_query(f"""
        SELECT
            ef.data_fechamento,
            CASE
                WHEN ef.empresa ILIKE '%TOOLS%'      THEN 'Tools'
                WHEN ef.empresa ILIKE '%MAQUINAS%'   THEN 'Maquinas'
                WHEN ef.empresa ILIKE '%ALLSERVICE%' THEN 'Service'
                WHEN ef.empresa ILIKE '%ROBOTICA%'   THEN 'Robotica'
                ELSE ef.empresa
            END AS empresa_norm,
            ef.filial,
            eu.empresa AS empresa_usadas,
            ef.produto,
            ef.descricao,
            ef.unid,
            ef.saldo_atual,
            ef.vlr_unit,
            ef.custo_total
        FROM estoque_fechamentos ef
        JOIN estoque_usadas eu ON eu.codigo = ef.produto
            AND (
                CASE
                    WHEN ef.empresa ILIKE '%TOOLS%'      THEN 'Tools'
                    WHEN ef.empresa ILIKE '%MAQUINAS%'   THEN 'Maquinas'
                    WHEN ef.empresa ILIKE '%ALLSERVICE%' THEN 'Service'
                    WHEN ef.empresa ILIKE '%ROBOTICA%'   THEN 'Robotica'
                    ELSE ef.empresa
                END
            ) = eu.empresa
        WHERE ef.produto IN ({placeholders})
        ORDER BY ef.data_fechamento, ef.produto
    """, params)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

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

codigos_tuple = tuple(df_usadas["codigo"].tolist()) if not df_usadas.empty else ()
try:
    df_hist = carregar_historico(codigos_tuple)
except Exception:
    df_hist = pd.DataFrame()

# -------------------------------------------------
# KPIs
# -------------------------------------------------

total_cadastradas = len(df_usadas)
total_usadas_qt = (df_usadas["tipo"] == "Maquina Usada").sum() if not df_usadas.empty else 0
total_novas_qt  = (df_usadas["tipo"] == "Máquina Nova").sum()  if not df_usadas.empty else 0

if not df_hist.empty:
    df_hist["data_fechamento"] = pd.to_datetime(df_hist["data_fechamento"])
    ultimo_fechamento = df_hist["data_fechamento"].max().strftime("%d/%m/%Y")
    df_ultimo = df_hist[df_hist["data_fechamento"] == df_hist["data_fechamento"].max()]
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
        <div class="kpi-value">{total_usadas_qt} / {total_novas_qt}</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-title">Valor em Estoque</div>
        <div class="kpi-value">{moeda(valor_total) if valor_total else "—"}</div>
        <div class="kpi-sub">Último: {ultimo_fechamento}</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-title">Unidades em Estoque</div>
        <div class="kpi-value">{f"{qtd_total:,.0f}" if qtd_total else "—"}</div>
        <div class="kpi-sub">Último: {ultimo_fechamento}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

aba_cadastro, aba_historico = st.tabs(["📋 Cadastro", "📈 Histórico"])

EMPRESAS_OPCOES = ["Tools", "Maquinas", "Robotica", "Service"]
TIPOS_OPCOES    = ["Maquina Usada", "Máquina Nova"]

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
            if st.form_submit_button("➕ Adicionar", type="primary", use_container_width=True):
                if not novo_codigo.strip():
                    st.error("Informe o código do produto.")
                else:
                    try:
                        db_exec(
                            "INSERT INTO estoque_usadas (empresa, codigo, tipo, descricao) "
                            "VALUES (:empresa, :codigo, :tipo, :descricao)",
                            {"empresa": nova_empresa, "codigo": novo_codigo.strip(),
                             "tipo": novo_tipo, "descricao": nova_desc.strip() or None}
                        )
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
                id_remover = int(df_usadas.iloc[idx]["id"])
                try:
                    db_exec("DELETE FROM estoque_usadas WHERE id = :id", {"id": id_remover})
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
            st.subheader("Evolução do Valor em Estoque")
            df_ev = (
                df_filtrado.groupby("data_fechamento")["custo_total"]
                .sum().reset_index().sort_values("data_fechamento")
            )
            st.line_chart(df_ev.set_index("data_fechamento")["custo_total"])

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
                st.dataframe(
                    df_pivot.style.format(lambda v: moeda(v) if pd.notna(v) else "—"),
                    use_container_width=True
                )
            except Exception:
                pass
