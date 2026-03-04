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

[data-baseweb="select"]{
    border:1px solid #EC6E21 !important;
    border-radius:6px !important;
}

[data-baseweb="popover"]{
    border:1px solid #EC6E21 !important;
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

# -------------------------------------------------
# STATUS DO ESTOQUE
# -------------------------------------------------

status_estoque = st.sidebar.selectbox(
    "Status do Estoque",
    ["Geral", "Obsoletos"]
)

# -------------------------------------------------
# EMPRESA / FILIAL
# -------------------------------------------------

empresas_lista = sorted(df_hist["Empresa / Filial"].dropna().unique())

empresas_sel = st.sidebar.multiselect(
    "Empresa / Filial",
    options=empresas_lista,
    default=[]
)

# -------------------------------------------------
# CONTA
# -------------------------------------------------

contas_lista = sorted(df_hist["Conta"].dropna().unique())

contas_sel = st.sidebar.multiselect(
    "Conta",
    options=contas_lista,
    default=[]
)

# -------------------------------------------------
# APLICAR FILTROS
# -------------------------------------------------

df_filtrado = df_hist.copy()

if status_estoque == "Obsoletos":
    df_filtrado = df_filtrado[
        df_filtrado["Status do Movimento"] != "Até 6 meses"
    ]

if empresas_sel:
    df_filtrado = df_filtrado[df_filtrado["Empresa / Filial"].isin(empresas_sel)]

if contas_sel:
    df_filtrado = df_filtrado[df_filtrado["Conta"].isin(contas_sel)]

# -------------------------------------------------
# SEM DADOS
# -------------------------------------------------

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
        x=alt.X("Fechamento:N", sort=ordem),
        y="Valor:Q",
        color="Tipo:N"
    ).properties(height=280)

    st.altair_chart(chart, use_container_width=True)

# =================================================
# TOP 20 PRODUTOS
# =================================================

with tab3:

    st.subheader("Top 20 Produtos Obsoletos")

    ultima_data = df_filtrado["Data Fechamento"].max()

    top20 = (
        df_filtrado[
            (df_filtrado["Data Fechamento"] == ultima_data) &
            (df_filtrado["Status Estoque"] == "Obsoleto")
        ]
        .sort_values("Custo Total", ascending=False)
        .head(20)
    )

    tabela_top20 = top20[
        [
            "Empresa / Filial",
            "Conta",
            "Produto",
            "Descricao",
            "Saldo Atual",
            "Vlr Unit",
            "Custo Total",
            "Meses Ult Mov",
            "Status do Movimento"
        ]
    ].copy()

    tabela_top20["Vlr Unit"] = tabela_top20["Vlr Unit"].apply(moeda_br)
    tabela_top20["Custo Total"] = tabela_top20["Custo Total"].apply(moeda_br)

    st.dataframe(tabela_top20, use_container_width=True)

# =================================================
# GRÁFICOS
# =================================================

with tab4:

    st.subheader("Gráficos de Análise")

    ultima_data = df_filtrado["Data Fechamento"].max()

    base = df_filtrado[df_filtrado["Data Fechamento"] == ultima_data]

    total_estoque = base["Custo Total"].sum()

    # =================================================
    # EMPRESA
    # =================================================

    empresa = (
        base.groupby("Empresa / Filial")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Custo Total", ascending=False)
    )

    empresa["perc"] = empresa["Custo Total"] / total_estoque

    empresa["label"] = empresa.apply(
        lambda x: f'{moeda_br(x["Custo Total"])} ({x["perc"]*100:.1f}%)',
        axis=1
    )

    bars = alt.Chart(empresa).mark_bar(color="#EC6E21").encode(
        x="Custo Total:Q",
        y=alt.Y("Empresa / Filial:N", sort="-x")
    )

    text = alt.Chart(empresa).mark_text(
        align="left",
        dx=3,
        color="white"
    ).encode(
        x="Custo Total:Q",
        y=alt.Y("Empresa / Filial:N", sort="-x"),
        text="label"
    )

    st.altair_chart((bars + text).properties(height=400), use_container_width=True)

    st.markdown("---")

    # =================================================
    # STATUS MOVIMENTO
    # =================================================

    status = (
        base.groupby("Status do Movimento")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Custo Total", ascending=False)
    )

    status["perc"] = status["Custo Total"] / total_estoque

    status["label"] = status.apply(
        lambda x: f'{moeda_br(x["Custo Total"])} ({x["perc"]*100:.1f}%)',
        axis=1
    )

    bars = alt.Chart(status).mark_bar(color="#EC6E21").encode(
        x="Custo Total:Q",
        y=alt.Y("Status do Movimento:N", sort="-x")
    )

    text = alt.Chart(status).mark_text(
        align="left",
        dx=3,
        color="white"
    ).encode(
        x="Custo Total:Q",
        y=alt.Y("Status do Movimento:N", sort="-x"),
        text="label"
    )

    st.altair_chart((bars + text).properties(height=300), use_container_width=True)

    st.markdown("---")

    # =================================================
    # CONTA
    # =================================================

    conta = (
        base.groupby("Conta")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Custo Total", ascending=False)
    )

    conta["perc"] = conta["Custo Total"] / total_estoque

    conta["label"] = conta.apply(
        lambda x: f'{moeda_br(x["Custo Total"])} ({x["perc"]*100:.1f}%)',
        axis=1
    )

    bars = alt.Chart(conta).mark_bar(color="#EC6E21").encode(
        x="Custo Total:Q",
        y=alt.Y("Conta:N", sort="-x")
    )

    text = alt.Chart(conta).mark_text(
        align="left",
        dx=3,
        color="white"
    ).encode(
        x="Custo Total:Q",
        y=alt.Y("Conta:N", sort="-x"),
        text="label"
    )

    st.altair_chart((bars + text).properties(height=300), use_container_width=True)
