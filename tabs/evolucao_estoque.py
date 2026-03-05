import streamlit as st
import pandas as pd
from analises import evolucao_estoque


def render(df_kpi, moeda_br):

    df_evolucao = evolucao_estoque(df_kpi)

    df_evolucao["Data Fechamento"] = pd.to_datetime(
        df_evolucao["Data Fechamento"]
    ).dt.date

    df_evolucao["Estoque Total"] = df_evolucao["Estoque Total"].apply(moeda_br)

    df_evolucao["Estoque Obsoleto"] = df_evolucao["Estoque Obsoleto"].apply(moeda_br)

    df_evolucao["% Obsoleto"] = (
        df_evolucao["% Obsoleto"] * 100
    ).round(2).astype(str) + "%"

    st.dataframe(
        df_evolucao,
        use_container_width=True,
        hide_index=True
    )
