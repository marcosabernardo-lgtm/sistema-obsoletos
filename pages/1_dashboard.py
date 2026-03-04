import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

from analises import evolucao_estoque

st.set_page_config(page_title="Dashboard Estoque", layout="wide")

st.title("📊 Dashboard de Estoque Obsoleto")

st.markdown("---")

# -------------------------------------------------
# CSS (cor azul nos filtros)
# -------------------------------------------------

st.markdown("""
<style>
span[data-baseweb="tag"]{
    background-color:#1f77b4 !important;
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

status_mov_opcoes = ["Todos"] + sorted(df_hist["Status do Movimento"].dropna().unique())

status_mov_sel = st.sidebar.selectbox(
    "Status do Movimento",
    status_mov_opcoes
)

# -------------------------------------------------
# APLICAR FILTROS
# -------------------------------------------------

df_filtrado = df_hist.copy()

if empresas_sel:
    df_filtrado = df_filtrado[df_filtrado["Empresa / Filial"].isin(empresas_sel)]

if contas_sel:
    df_filtrado = df_filtrado[df_filtrado["Conta"].isin(contas_sel)]

if status_mov_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Status do Movimento"] == status_mov_sel]

if df_filtrado.empty:
    st.warning("Sem dados para os filtros selecionados.")
    st.stop()

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1, tab2 = st.tabs([
    "📚 Base Histórica",
    "📈 Evolução do Estoque"
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
# EVOLUÇÃO DO ESTOQUE
# =================================================

with tab2:

    df_evolucao = evolucao_estoque(df_filtrado)

    df_evolucao = df_evolucao.sort_values("Data Fechamento")

    ultimo = df_evolucao.iloc[-1]

    estoque_total = ultimo["Estoque Total"]
    estoque_obsoleto = ultimo["Estoque Obsoleto"]
    percentual = ultimo["% Obsoleto"]

    ultima_data = df_filtrado["Data Fechamento"].max()

    itens_obsoletos = df_filtrado[
        (df_filtrado["Data Fechamento"] == ultima_data) &
        (df_filtrado["Status Estoque"] == "Obsoleto")
    ].shape[0]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Estoque Total", moeda_br(estoque_total))
    col2.metric("Estoque Obsoleto", moeda_br(estoque_obsoleto))
    col3.metric("% Obsolescência", f"{percentual*100:.2f}%")
    col4.metric("Itens Obsoletos", f"{itens_obsoletos:,}".replace(",", "."))

    st.markdown("---")

    # -------------------------------------------------
    # TABELA EVOLUÇÃO
    # -------------------------------------------------

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
        [
            "Fechamento",
            "Estoque Total",
            "Estoque Obsoleto",
            "% Obsoleto"
        ]
    ]

    st.subheader("Evolução do Estoque")

    st.dataframe(df_tabela, use_container_width=True)

    # -------------------------------------------------
    # GRÁFICO EVOLUÇÃO
    # -------------------------------------------------

    df_chart = df_evolucao.copy()

    df_chart["Data Fechamento"] = pd.to_datetime(df_chart["Data Fechamento"])

    df_chart = df_chart.sort_values("Data Fechamento")

    df_chart["Fechamento"] = df_chart["Data Fechamento"].dt.strftime("%m/%Y")

    df_chart = df_chart.melt(
        id_vars=["Data Fechamento", "Fechamento"],
        value_vars=["Estoque Total", "Estoque Obsoleto"],
        var_name="Tipo",
        value_name="Valor"
    )

    ordem = df_chart["Fechamento"].drop_duplicates().tolist()

    chart = alt.Chart(df_chart).mark_line(point=True).encode(
        x=alt.X(
            "Fechamento:N",
            sort=ordem,
            axis=alt.Axis(labelAngle=0),
            title="Fechamento"
        ),
        y=alt.Y(
            "Valor:Q",
            title="Valor"
        ),
        color=alt.Color(
            "Tipo:N",
            title="Tipo"
        )
    ).properties(
        height=280
    )

    st.altair_chart(chart, use_container_width=True)

    st.markdown("---")

    # =================================================
    # TOP 20 PRODUTOS OBSOLETOS
    # =================================================

    st.subheader("Top 20 Produtos Obsoletos")

    top_produtos = (
        df_filtrado[df_filtrado["Status Estoque"] == "Obsoleto"]
        .groupby(["Produto", "Descricao"], as_index=False)["Custo Total"]
        .sum()
        .sort_values("Custo Total", ascending=False)
        .head(20)
    )

    fig_prod = px.bar(
        top_produtos,
        x="Custo Total",
        y="Descricao",
        orientation="h"
    )

    fig_prod.update_layout(height=600)

    st.plotly_chart(fig_prod, use_container_width=True)

    # =================================================
    # TOP 5 EMPRESAS
    # =================================================

    st.subheader("Top 5 Empresas com Maior Estoque Obsoleto")

    top_empresas = (
        df_filtrado[df_filtrado["Status Estoque"] == "Obsoleto"]
        .groupby("Empresa / Filial", as_index=False)["Custo Total"]
        .sum()
        .sort_values("Custo Total", ascending=False)
        .head(5)
    )

    fig_emp = px.bar(
        top_empresas,
        x="Empresa / Filial",
        y="Custo Total"
    )

    fig_emp.update_layout(height=400)

    st.plotly_chart(fig_emp, use_container_width=True)

    # =================================================
    # CURVA DE ENVELHECIMENTO
    # =================================================

    st.subheader("Curva de Envelhecimento do Estoque")

    curva = (
        df_filtrado.groupby("Status do Movimento", as_index=False)["Custo Total"]
        .sum()
        .sort_values("Custo Total", ascending=False)
    )

    fig_curva = px.bar(
        curva,
        x="Status do Movimento",
        y="Custo Total"
    )

    fig_curva.update_layout(height=400)

    st.plotly_chart(fig_curva, use_container_width=True)
