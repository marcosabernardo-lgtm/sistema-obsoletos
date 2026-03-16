import streamlit as st
import pandas as pd

st.title("📊 Dashboard de Inventário")

df = pd.read_parquet("data/inventario/inventario_historico.parquet")

st.write("Base de Inventário")
st.dataframe(df)