import streamlit as st
import pandas as pd

from tabs.estoque.evolucao_estoque_total import render as render_estoque_total


st.set_page_config(page_title="Dashboard Estoque", layout="wide")

st.title("📦 Dashboard Evolução de Estoque")

st.markdown("---")

# -------------------------------------------------
# CARREGAR BASE DE ESTOQUE
# -------------------------------------------------

df_hist = pd.read_parquet("data/base_estoque.parquet")

# -------------------------------------------------
# RENDER
# -------------------------------------------------

render_estoque_total(df_hist)