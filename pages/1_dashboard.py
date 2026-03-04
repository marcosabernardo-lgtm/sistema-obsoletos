import streamlit as st
import pandas as pd
import altair as alt

from analises import evolucao_estoque

st.set_page_config(page_title="Dashboard Estoque", layout="wide")

st.title("📊 Dashboard de Estoque Obsoleto")

st.markdown("---")

# -------------------------------------------------
# Upload manual do histórico
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
# Carregar histórico
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

st.markdown("---")

# -------------------------------------------------
# Criar abas
# -------------------------------------------------

tab1, tab2 = st.tabs([
    "📚 Base Histórica",
    "📈 Evolução do Estoque"
])

# =================================================
# ABA 1 - BASE HISTÓRICA
# =================================================

with tab1:

    st.subheader("Base Histórica")

    df_hist["Data Fechamento"] = pd.to_datetime(
        df_hist["Data Fechamento"]
    ).dt.date

    st.dataframe(df_hist)

# =================================================
# ABA 2 - EVOLUÇÃO DO ESTOQUE
# =================================================

with tab2:

    df_evolucao = evolucao_estoque(df_hist)

    # -----------------------------
    # KPIs
    # -----------------------------

    ultimo = df_evolucao.sort_values("Data Fechamento").iloc[-1]

    estoque_total = ultimo["Estoque Total"]
    estoque_obsoleto = ultimo["Estoque Obsoleto"]
    percentual = ultimo["% Obsoleto"]

    ultima_data = df_hist["Data Fechamento"].max()

    itens_obsoletos = df_hist[
        (df_hist["Data Fechamento"] == ultima_data) &
        (df_hist["Status Estoque"] == "Obsoleto")
    ].shape[0]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Estoque Total", f"R$ {estoque_total:,.0f}")
    col2.metric("Estoque Obsoleto", f"R$ {estoque_obsoleto:,.0f}")
    col3.metric("% Obsolescência", f"{percentual*100:.2f}%")
    col4.metric("Itens Obsoletos", f"{itens_obsoletos:,}")

    st.markdown("---")

    # -----------------------------
    # TABELA EVOLUÇÃO
    # -----------------------------

    df_tabela = df_evolucao.copy()

    df_tabela["Fechamento"] = pd.to_datetime(
        df_tabela["Data Fechamento"]
    ).dt.strftime("%m/%Y")

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

    # -----------------------------
    # GRÁFICO
    # -----------------------------

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

    ordem_fechamentos = df_chart["Fechamento"].drop_duplicates().tolist()

    chart = alt.Chart(df_chart).mark_line(point=True).encode(
        x=alt.X(
            "Fechamento:N",
            sort=ordem_fechamentos,
            title="Fechamento",
            axis=alt.Axis(labelAngle=0)
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
        height=260
    )

    st.altair_chart(chart, use_container_width=True)
