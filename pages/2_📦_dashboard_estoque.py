import streamlit as st
import pandas as pd
import os
import glob

from tabs.estoque.evolucao_estoque_total import render as render_estoque_total


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
# RENDER
# -------------------------------------------------

render_estoque_total(df_hist)