import streamlit as st
import pandas as pd
import altair as alt

from analises import evolucao_estoque

st.set_page_config(page_title="Dashboard Estoque", layout="wide")

st.title("📊 Dashboard de Estoque Obsoleto")

st.markdown("---")

# -------------------------------------------------
# CSS GLOBAL
# -------------------------------------------------

st.markdown("""
<style>

span[data-baseweb="tag"]{
    background-color:#1f77b4 !important;
}

div[data-baseweb="select"] > div{
    border:1px solid #EC6E21 !important;
}

/* HEADER DAS TABELAS */

thead tr th{
    background-color:#005562 !important;
    color:white !important;
    font-weight:600 !important;
}

/* remove zebra default */

tbody tr{
    background-color:#0f5a60 !important;
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# FORMATAÇÃO BR
# -------------------------------------------------

def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# -------------------------------------------------
# Upload histórico
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
# Carregar base
# -------------------------------------------------

try:
    df_hist = pd.read_parquet("data/base_historica.parquet")
except:
    st.warning("Nenhum histórico encontrado.")
    st.stop()

# -------------------------------------------------
# Download histórico
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
    ["Geral", "Obsoletos"]
)

empresas_lista = sorted(df_hist["Empresa / Filial"].dropna().unique())

empresas_sel = st.sidebar.multiselect(
    "Empresa / Filial",
    options=empresas_lista,
    default=[]
)

contas_lista = sorted(df_hist["Conta"].dropna().unique())

contas_sel = st.sidebar.multiselect(
    "Conta",
    options=contas_lista,
    default=[]
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

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs([
    "📚 Base Histórica",
    "📈 Evolução do Estoque",
    "🏆 Top 20 Produtos",
    "📊 Gráficos"
])

# =================================================
# BASE HISTÓRICA
# =================================================

with tab1:

    st.subheader("Base Histórica")

    df_base = df_filtrado.copy()

    df_base["Data Fechamento"] = pd.to_datetime(
        df_base["Data Fechamento"]
    ).dt.date

    df_base["Custo Total"] = df_base["Custo Total"].apply(moeda_br)
    df_base["Vlr Unit"] = df_base["Vlr Unit"].apply(moeda_br)

    st.dataframe(df_base, use_container_width=True)

# =================================================
# EVOLUÇÃO
# =================================================

with tab2:

    df_evolucao = evolucao_estoque(df_kpi)

    df_evolucao = df_evolucao.sort_values("Data Fechamento")

    df_tabela = df_evolucao.copy()

    df_tabela["Fechamento"] = pd.to_datetime(
        df_tabela["Data Fechamento"]
    ).dt.strftime("%m/%Y")

    df_tabela["Estoque Total"] = df_tabela["Estoque Total"].apply(moeda_br)
    df_tabela["Estoque Obsoleto"] = df_tabela["Estoque Obsoleto"].apply(moeda_br)

    df_tabela["% Obsoleto"] = (
        df_tabela["% Obsoleto"] * 100
    ).map(lambda x: f"{x:.2f}%")

    df_tabela = df_tabela[
        ["Fechamento","Estoque Total","Estoque Obsoleto","% Obsoleto"]
    ]

    st.dataframe(df_tabela, use_container_width=True)

# =================================================
# TOP 20
# =================================================

with tab3:

    st.subheader("Top 20 Produtos Obsoletos")

    ultima_data = df_filtrado["Data Fechamento"].max()

    top20 = (
        df_filtrado[df_filtrado["Data Fechamento"] == ultima_data]
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

    st.dataframe(top20, use_container_width=True)

# =================================================
# GRÁFICOS
# =================================================

with tab4:

    ultima_data = df_filtrado["Data Fechamento"].max()

    base = df_filtrado[
        df_filtrado["Data Fechamento"] == ultima_data
    ]

    # -------------------------------------------------
    # EMPRESA
    # -------------------------------------------------

    st.subheader("Obsoleto por Empresa / Filial")

    empresa = (
        base.groupby("Empresa / Filial")["Custo Total"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    empresa["%"] = empresa["Custo Total"] / empresa["Custo Total"].sum()

    empresa["Label"] = empresa.apply(
        lambda x: f'{moeda_br(x["Custo Total"])} ({x["%"]*100:.1f}%)',
        axis=1
    )

    max_x = empresa["Custo Total"].max() * 1.15

    chart1 = alt.Chart(empresa).mark_bar(color="#EC6E21").encode(
        x=alt.X(
            "Custo Total",
            scale=alt.Scale(domain=[0,max_x]),
            axis=None
        ),
        y=alt.Y(
            "Empresa / Filial",
            sort="-x",
            axis=alt.Axis(title=None,labelLimit=400)
        )
    )

    text1 = alt.Chart(empresa).mark_text(
        align="left",
        dx=5,
        color="white"
    ).encode(
        x="Custo Total",
        y=alt.Y("Empresa / Filial",sort="-x"),
        text="Label"
    )

    st.altair_chart(chart1 + text1, use_container_width=True)

    # -------------------------------------------------
    # STATUS MOVIMENTO
    # -------------------------------------------------

    st.subheader("Obsoleto por Status do Movimento")

    status = (
        base.groupby("Status do Movimento")["Custo Total"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    status["%"] = status["Custo Total"] / status["Custo Total"].sum()

    status["Label"] = status.apply(
        lambda x: f'{moeda_br(x["Custo Total"])} ({x["%"]*100:.1f}%)',
        axis=1
    )

    max_x = status["Custo Total"].max() * 1.15

    chart2 = alt.Chart(status).mark_bar(color="#EC6E21").encode(
        x=alt.X(
            "Custo Total",
            scale=alt.Scale(domain=[0,max_x]),
            axis=None
        ),
        y=alt.Y(
            "Status do Movimento",
            sort="-x",
            axis=alt.Axis(title=None,labelLimit=400)
        )
    )

    text2 = alt.Chart(status).mark_text(
        align="left",
        dx=5,
        color="white"
    ).encode(
        x="Custo Total",
        y=alt.Y("Status do Movimento",sort="-x"),
        text="Label"
    )

    st.altair_chart(chart2 + text2, use_container_width=True)

    # -------------------------------------------------
    # CONTA
    # -------------------------------------------------

    st.subheader("Obsoleto por Conta")

    conta = (
        base.groupby("Conta")["Custo Total"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    conta["%"] = conta["Custo Total"] / conta["Custo Total"].sum()

    conta["Label"] = conta.apply(
        lambda x: f'{moeda_br(x["Custo Total"])} ({x["%"]*100:.1f}%)',
        axis=1
    )

    max_x = conta["Custo Total"].max() * 1.15

    chart3 = alt.Chart(conta).mark_bar(color="#EC6E21").encode(
        x=alt.X(
            "Custo Total",
            scale=alt.Scale(domain=[0,max_x]),
            axis=None
        ),
        y=alt.Y(
            "Conta",
            sort="-x",
            axis=alt.Axis(title=None,labelLimit=400)
        )
    )

    text3 = alt.Chart(conta).mark_text(
        align="left",
        dx=5,
        color="white"
    ).encode(
        x="Custo Total",
        y=alt.Y("Conta",sort="-x"),
        text="Label"
    )

    st.altair_chart(chart3 + text3, use_container_width=True)
