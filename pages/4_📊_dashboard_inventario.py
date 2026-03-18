import streamlit as st
import pandas as pd

from utils.navbar import render_navbar

st.set_page_config(page_title="Dashboard Inventário", layout="wide")
render_navbar("Dashboard Inventário")

st.title("📊 Dashboard de Inventário")

df = pd.read_parquet("data/inventario/inventario_historico.parquet")

st.write("Base de Inventário")
st.dataframe(df)