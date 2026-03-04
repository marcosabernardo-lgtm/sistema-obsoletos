import streamlit as st
import pandas as pd

from analises import evolucao_estoque

st.set_page_config(page_title="Dashboard Estoque", layout="wide")

st.title("📊 Dashboard de Estoque Obsoleto")

st.markdown("---")

# Upload manual do histórico (caso o servidor reinicie)
uploaded_hist = st.file_uploader(
    "📤 Carregar Histórico (arquivo base_historica.parquet)",
    type=["parquet"]
)

if uploaded_hist is not None:
    df_hist = pd.read_parquet(uploaded_hist)
    df_hist.to_parquet("data/base_historica.parquet", index=False)
    st.success("Histórico carregado com sucesso!")

# Tentar carregar histórico existente
try:
    df_hist = pd.read_parquet("data/base_historica.parquet")
except:
    st.warning("Nenhum histórico encontrado. Faça upload do histórico ou processe um fechamento.")
    st.stop()

# botão de download do histórico
with open("data/base_historica.parquet", "rb") as f:
    st.download_button(
        label="📥 Baixar Histórico",
        data=f,
        file_name="base_historica.parquet"
    )

st.markdown("---")

# Ajustar data
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
