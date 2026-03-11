import streamlit as st
import pandas as pd
import glob

from tabs.estoque.evolucao_estoque import render as render_evolucao_estoque


st.set_page_config(page_title="Dashboard Estoque", layout="wide")

st.title("📦 Dashboard Evolução de Estoque")

st.markdown("---")


# -------------------------------------------------
# FUNÇÃO MOEDA
# -------------------------------------------------

def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# -------------------------------------------------
# PASTA DATA LAKE
# -------------------------------------------------

PASTA = "data/estoque"


# -------------------------------------------------
# VERIFICAR SE EXISTEM FECHAMENTOS
# -------------------------------------------------

arquivos = glob.glob(f"{PASTA}/*.parquet")

if len(arquivos) == 0:

    st.info("Nenhum fechamento de estoque processado ainda.")

    st.markdown("""
Para utilizar este dashboard:

1️⃣ Vá para a página **app**  
2️⃣ Faça upload escolhendo **Atualizar Evolução de Estoque**
""")

    st.stop()


# -------------------------------------------------
# CARREGAR TODOS OS FECHAMENTOS
# -------------------------------------------------

dfs = []

for arq in arquivos:
    df = pd.read_parquet(arq)
    dfs.append(df)

df_hist = pd.concat(dfs, ignore_index=True)


# -------------------------------------------------
# TRATAR DADOS
# -------------------------------------------------

if df_hist.empty:
    st.warning("⚠️ Base de dados vazia.")
    st.stop()

df_hist["Custo Total"] = pd.to_numeric(df_hist["Custo Total"], errors="coerce").fillna(0)
df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"])


# -------------------------------------------------
# RENDER
# -------------------------------------------------

try:
    render_evolucao_estoque(df_hist, moeda_br)

except Exception as e:
    st.exception(e)