import streamlit as st
import pandas as pd
import os

from tabs.estoque.evolucao_estoque import render as render_evolucao_estoque


st.set_page_config(
    page_title="Dashboard Estoque",
    layout="wide"
)

st.title("📦 Dashboard Evolução de Estoque")

st.markdown("---")


# -------------------------------------------------
# FUNÇÃO MOEDA
# -------------------------------------------------

def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# -------------------------------------------------
# CAMINHO DO DATA LAKE
# -------------------------------------------------

CAMINHO_BASE = "data/estoque/estoque_historico.parquet"


# -------------------------------------------------
# VERIFICAR SE EXISTE BASE
# -------------------------------------------------

if not os.path.exists(CAMINHO_BASE):

    st.info("Nenhum fechamento de estoque processado ainda.")

    st.markdown("""
Para utilizar este dashboard:

1️⃣ Vá para a página **app**  
2️⃣ Faça upload escolhendo **Atualizar Evolução de Estoque**
""")

    st.stop()


# -------------------------------------------------
# CARREGAR BASE HISTÓRICA
# -------------------------------------------------

try:

    df_hist = pd.read_parquet(CAMINHO_BASE)

except Exception as e:

    st.error("Erro ao carregar a base de estoque.")
    st.exception(e)
    st.stop()


# -------------------------------------------------
# TRATAMENTO DOS DADOS
# -------------------------------------------------

if df_hist.empty:

    st.warning("⚠️ Base de dados vazia.")
    st.stop()

df_hist["Custo Total"] = pd.to_numeric(
    df_hist["Custo Total"],
    errors="coerce"
).fillna(0)

df_hist["Data Fechamento"] = pd.to_datetime(
    df_hist["Data Fechamento"],
    errors="coerce"
)


# -------------------------------------------------
# ORDENAR HISTÓRICO
# -------------------------------------------------

df_hist = df_hist.sort_values("Data Fechamento")


# -------------------------------------------------
# RENDER DASHBOARD
# -------------------------------------------------

try:

    render_evolucao_estoque(
        df_hist,
        moeda_br
    )

except Exception as e:

    st.error("Erro ao renderizar o dashboard.")
    st.exception(e)