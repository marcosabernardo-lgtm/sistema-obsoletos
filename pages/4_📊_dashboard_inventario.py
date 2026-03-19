import streamlit as st
import pandas as pd

from utils.navbar import render_navbar

st.set_page_config(page_title="Dashboard Inventário", layout="wide")
render_navbar("Dashboard Inventário")

st.title("📊 Dashboard de Inventário")

df = pd.read_parquet("data/inventario/inventario_historico.parquet")

# -------------------------------------------------
# TRATAMENTO
# -------------------------------------------------

# Data sem hora
df["Data_Inventario"] = pd.to_datetime(df["Data_Inventario"]).dt.date

# Renomear colunas
df = df.rename(columns={
    "Data_Inventario":      "Data Inventario",
    "Nome_Empresa":         "Empresa / Filial",
    "Codigo":               "Produto",
    "Descricao":            "Descricao",
    "Qtd_Inventariada":     "Qtd Inventariada",
    "Qtd_Protheus":         "Qtd Protheus",
    "Qtd_Divergente":       "Qtd Divergente",
    "Valor_Unitario":       "Valor Unitario",
    "Valor_Protheus":       "Valor Protheus",
    "Valor_Inventariado":   "Valor Inventariado",
    "Valor_Divergente":     "Valor Divergente",
})

# Remover colunas desnecessárias
colunas_remover = ["Empresa", "Qtd Itens Inventariados", "Qtd Itens Divergentes"]
df = df.drop(columns=[c for c in colunas_remover if c in df.columns], errors="ignore")

# Ordem final das colunas
colunas_ordem = [
    "Data Inventario",
    "Empresa / Filial",
    "Produto",
    "Descricao",
    "Qtd Inventariada",
    "Valor Inventariado",
    "Qtd Protheus",
    "Valor Protheus",
    "Qtd Divergente",
    "Valor Divergente",
]

df = df[[c for c in colunas_ordem if c in df.columns]]

# -------------------------------------------------
# EXIBIÇÃO
# -------------------------------------------------

st.write("Base de Inventário")
st.dataframe(df, use_container_width=True)
