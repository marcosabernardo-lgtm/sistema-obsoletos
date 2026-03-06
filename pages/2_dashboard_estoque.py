import streamlit as st
import pandas as pd
import os

from tabs.estoque.evolucao_estoque_total import render as render_estoque_total


st.set_page_config(page_title="Dashboard Estoque", layout="wide")

st.title("📦 Dashboard Evolução de Estoque")

st.markdown("---")

CAMINHO_BASE = "data/base_estoque.parquet"

# -------------------------------------------------
# VERIFICAR SE BASE EXISTE
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
# CARREGAR BASE
# -------------------------------------------------

df_hist = pd.read_parquet(CAMINHO_BASE)

# -------------------------------------------------
# RENDER
# -------------------------------------------------

render_estoque_total(df_hist)