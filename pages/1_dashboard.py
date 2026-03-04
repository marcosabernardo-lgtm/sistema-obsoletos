import streamlit as st
import pandas as pd

from analises import evolucao_estoque

st.set_page_config(page_title="Dashboard Estoque", layout="wide")

st.title("📊 Dashboard de Estoque Obsoleto")

st.markdown("---")

# -------------------------------------------------
# Upload manual do histórico (caso servidor reinicie)
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
# Tentar carregar histórico
# -------------------------------------------------

try:
    df_hist = pd.read_parquet("data/base_historica.parquet")
except:
    st.warning("Nenhum histórico encontrado.")
    st.stop()

# -------------------------------------------------
# Download do histórico
# -------------------------------------------------

with open("data/base_historica.parquet", "rb") as f:
    st.download_button(
        label="📥 Baixar Histórico",
        data=f,
        file_name="base_historica.parquet"
    )

st.markdown("---")

# -------------------------------------------------
# Criar abas
# -------------------------------------------------

tab1, tab2 = st.tabs([
    "📚 Base Histórica",
    "📈 Evolução do Estoque"
])

# -------------------------------------------------
# ABA 1 - BASE HISTORICA
# -------------------------------------------------

with tab1:

    df_hist["Data Fechamento"] = pd.to_datetime(
        df_hist["Data Fechamento"]
    ).dt.date

    st.subheader("Base Histórica")

    st.dataframe(df_hist)

# -------------------------------------------------
# ABA 2 - EVOLUÇÃO
# -------------------------------------------------

with tab2:

    df_evolucao = evolucao_estoque(df_hist)

    # criar coluna de fechamento mensal
    df_evolucao["Fechamento"] = pd.to_datetime(
        df_evolucao["Data Fechamento"]
    ).dt.strftime("%m/%Y")

    # -------------------------------------------------
    # TABELA FORMATADA
    # -------------------------------------------------

    df_tabela = df_evolucao.copy()

    df_tabela["Estoque Total"] = df_tabela["Estoque Total"].map(
        lambda x: f"R$ {x:,.2f}"
    )

    df_tabela["Estoque Obsoleto"] = df_tabela["Estoque Obsoleto"].map(
        lambda x: f"R$ {x:,.2f}"
    )

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

    st.dataframe(df_tabela)

    # -------------------------------------------------
    # GRÁFICO
    # -------------------------------------------------

import altair as alt

# preparar dados
df_chart = df_evolucao.copy()

df_chart["Data Fechamento"] = pd.to_datetime(df_chart["Data Fechamento"])

# transformar para formato longo
df_chart = df_chart.melt(
    id_vars="Data Fechamento",
    value_vars=["Estoque Total", "Estoque Obsoleto"],
    var_name="Tipo",
    value_name="Valor"
)

# criar gráfico
chart = alt.Chart(df_chart).mark_line(point=True).encode(
    x=alt.X(
        "yearmonth(Data Fechamento):T",
        title="Fechamento",
        axis=alt.Axis(format="%m/%Y", labelAngle=0)
    ),
    y=alt.Y("Valor:Q", title="Valor"),
    color=alt.Color("Tipo:N", title="Tipo")
).properties(
    height=400
)

st.altair_chart(chart, use_container_width=True)
