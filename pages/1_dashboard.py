import streamlit as st
import pandas as pd
import altair as alt

from analises import evolucao_estoque

st.set_page_config(page_title="Dashboard Estoque", layout="wide")

st.title("📊 Dashboard de Estoque Obsoleto")

st.markdown("---")

# -------------------------------------------------
# CSS
# -------------------------------------------------

st.markdown("""
<style>

span[data-baseweb="tag"]{
    background-color:#1f77b4 !important;
}

div[data-baseweb="select"] > div{
    border:1px solid #EC6E21 !important;
}

thead tr th{
    background-color:#005562 !important;
    color:white !important;
    font-weight:600 !important;
}

tbody tr{
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

# -------------------------------------------------
# FUNÇÕES
# -------------------------------------------------

def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# -------------------------------------------------
# UPLOAD
# -------------------------------------------------

uploaded_hist = st.file_uploader(
    "📤 Carregar Histórico (arquivo base_historica.parquet)",
    type=["parquet"]
)

if uploaded_hist is not None:
    df_hist = pd.read_parquet(uploaded_hist)
    df_hist.to_parquet("data/base_historica.parquet", index=False)
    st.success("Histórico carregado com sucesso!")

# -------------------------------------------------
# CARREGAR BASE
# -------------------------------------------------

try:
    df_hist = pd.read_parquet("data/base_historica.parquet")
except:
    st.warning("Nenhum histórico encontrado.")
    st.stop()

# -------------------------------------------------
# DOWNLOAD
# -------------------------------------------------

with open("data/base_historica.parquet", "rb") as f:
    st.download_button(
        label="📥 Baixar Histórico",
        data=f,
        file_name="base_historica.parquet"
    )

# -------------------------------------------------
# FILTROS
# -------------------------------------------------

st.sidebar.header("Filtros")

status_estoque = st.sidebar.selectbox(
    "Status do Estoque",
    ["Geral","Obsoletos"]
)

empresas = sorted(df_hist["Empresa / Filial"].dropna().unique())

empresas_sel = st.sidebar.multiselect(
    "Empresa / Filial",
    options=empresas
)

contas = sorted(df_hist["Conta"].dropna().unique())

contas_sel = st.sidebar.multiselect(
    "Conta",
    options=contas
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

if df_filtrado.empty:
    st.warning("Sem dados para os filtros selecionados.")
    st.stop()

# -------------------------------------------------
# KPIs
# -------------------------------------------------

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
<div class="kpi-value">{itens_obsoletos:,}</div>
</div>
""",unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1,tab2,tab3,tab4 = st.tabs([
    "📚 Base Histórica",
    "📈 Evolução do Estoque",
    "🏆 Top 20 Produtos",
    "📊 Gráficos"
])

# =================================================
# BASE HISTÓRICA
# =================================================

with tab1:

    df_base = df_filtrado.copy()

    df_base["Custo Total"] = df_base["Custo Total"].apply(moeda_br)

    st.dataframe(df_base,use_container_width=True)

# =================================================
# EVOLUÇÃO
# =================================================

with tab2:

    df_evolucao = evolucao_estoque(df_kpi)

    df_evolucao = df_evolucao.sort_values("Data Fechamento")

    df_evolucao["Estoque Total"] = df_evolucao["Estoque Total"].apply(moeda_br)
    df_evolucao["Estoque Obsoleto"] = df_evolucao["Estoque Obsoleto"].apply(moeda_br)

    st.dataframe(df_evolucao,use_container_width=True)

# =================================================
# TOP 20
# =================================================

with tab3:

    st.subheader("Top 20 Produtos Obsoletos")

    ultima_data = df_filtrado["Data Fechamento"].max()

    top20 = (
        df_filtrado[df_filtrado["Data Fechamento"]==ultima_data]
        .groupby(["Empresa / Filial","Produto","Descricao"],as_index=False)
        .agg(
            Quantidade=("Saldo Atual","sum"),
            Custo_Total=("Custo Total","sum")
        )
        .sort_values("Custo_Total",ascending=False)
        .head(20)
    )

    top20 = top20.rename(columns={"Custo_Total":"Custo Total"})

    top20["Custo Total"] = top20["Custo Total"].apply(moeda_br)

    st.dataframe(top20,use_container_width=True)

# =================================================
# GRÁFICOS
# =================================================

with tab4:

    ultima_data = df_filtrado["Data Fechamento"].max()

    base = df_filtrado[
        df_filtrado["Data Fechamento"] == ultima_data
    ]

    # EMPRESA

    st.subheader("Obsoleto por Empresa / Filial")

    empresa = (
        base.groupby("Empresa / Filial")["Custo Total"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    empresa["%"] = empresa["Custo Total"]/empresa["Custo Total"].sum()

    empresa["Label"] = empresa.apply(
        lambda x: f'{moeda_br(x["Custo Total"])} ({x["%"]*100:.1f}%)',
        axis=1
    )

    chart = alt.Chart(empresa).mark_bar(color="#EC6E21").encode(
        x=alt.X("Custo Total",axis=None),
        y=alt.Y("Empresa / Filial",sort="-x",axis=alt.Axis(title=None))
    )

    text = alt.Chart(empresa).mark_text(
        align="left",
        dx=5,
        color="white"
    ).encode(
        x="Custo Total",
        y="Empresa / Filial",
        text="Label"
    )

    st.altair_chart(chart+text,use_container_width=True)

    # STATUS

    st.subheader("Obsoleto por Status do Movimento")

    status = (
        base.groupby("Status do Movimento")["Custo Total"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    chart = alt.Chart(status).mark_bar(color="#EC6E21").encode(
        x=alt.X("Custo Total",axis=None),
        y=alt.Y("Status do Movimento",sort="-x",axis=alt.Axis(title=None))
    )

    st.altair_chart(chart,use_container_width=True)

    # CONTA

    st.subheader("Obsoleto por Conta")

    conta = (
        base.groupby("Conta")["Custo Total"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    chart = alt.Chart(conta).mark_bar(color="#EC6E21").encode(
        x=alt.X("Custo Total",axis=None),
        y=alt.Y("Conta",sort="-x",axis=alt.Axis(title=None))
    )

    st.altair_chart(chart,use_container_width=True)
