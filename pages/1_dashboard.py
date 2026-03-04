import streamlit as st
import pandas as pd

from base_historica import atualizar_base_historica
from analises import evolucao_estoque

st.set_page_config(page_title="Dashboard Estoque", layout="wide")

st.title("📊 Dashboard de Estoque Obsoleto")

st.markdown("---")

# carregar histórico
try:
    df_hist = pd.read_parquet("data/base_historica.parquet")
except:
    st.warning("Nenhum histórico carregado ainda.")
    st.stop()

# ajustar data
df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"]).dt.date

st.subheader("📚 Base Histórica")

st.dataframe(df_hist)

st.markdown("---")

st.subheader("📈 Evolução do Estoque")

df_evolucao = evolucao_estoque(df_hist)

df_evolucao["Data Fechamento"] = pd.to_datetime(df_evolucao["Data Fechamento"]).dt.date

# tabela formatada
df_tabela = df_evolucao.copy()

df_tabela["Estoque Total"] = df_tabela["Estoque Total"].map(lambda x: f"R$ {x:,.2f}")
df_tabela["Estoque Obsoleto"] = df_tabela["Estoque Obsoleto"].map(lambda x: f"R$ {x:,.2f}")
df_tabela["% Obsoleto"] = (df_tabela["% Obsoleto"] * 100).map(lambda x: f"{x:.2f}%")

st.dataframe(df_tabela)

# gráfico
st.line_chart(
    df_evolucao.set_index("Data Fechamento")[
        ["Estoque Total", "Estoque Obsoleto"]
    ]
)
