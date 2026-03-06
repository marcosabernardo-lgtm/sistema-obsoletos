import streamlit as st
import pandas as pd
from utils.utils import botao_download_excel


def render(df_filtrado, moeda_br):

    ultima_data = df_filtrado["Data Fechamento"].max()

    base = df_filtrado[df_filtrado["Data Fechamento"] == ultima_data]

    top20 = (
        base
        .groupby(
            ["Empresa / Filial", "Conta", "Produto", "Descricao"],
            as_index=False
        )
        .agg(
            Quantidade=("Saldo Atual", "sum"),
            Custo_Total=("Custo Total", "sum")
        )
    )

    total_geral = top20["Custo_Total"].sum()

    top20["%"] = (top20["Custo_Total"] / total_geral) * 100

    top20 = (
        top20
        .sort_values("Custo_Total", ascending=False)
        .head(20)
    )

    top20.insert(0, "Ranking", range(1, len(top20) + 1))

    top20 = top20.rename(columns={"Custo_Total": "Custo Total"})

    # ---------- DATAFRAME PARA EXPORTAR ----------
    export_df = top20.copy()

    # ---------- FORMATAÇÃO PARA TELA ----------
    top20["Custo Total"] = top20["Custo Total"].apply(moeda_br)
    top20["%"] = top20["%"].apply(lambda x: f"{x:.2f}%")

    top20 = top20[
        [
            "Ranking",
            "Empresa / Filial",
            "Conta",
            "Produto",
            "Descricao",
            "Quantidade",
            "Custo Total",
            "%"
        ]
    ]

    # ---------- BOTÃO EXPORTAR ----------
    botao_download_excel(export_df, "top20_estoque_obsoleto.xlsx")

    # ---------- TABELA ----------
    st.dataframe(
        top20,
        use_container_width=True,
        hide_index=True
    )