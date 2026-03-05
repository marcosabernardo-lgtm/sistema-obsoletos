import streamlit as st
import pandas as pd
from analises import evolucao_estoque


def render(df_kpi, moeda_br):

    df_evolucao = evolucao_estoque(df_kpi)

    df_evolucao["Data Fechamento"] = pd.to_datetime(
        df_evolucao["Data Fechamento"]
    ).dt.date

    # ==========================================
    # CALCULAR VARIAÇÃO DO ESTOQUE TOTAL
    # ==========================================

    df_evolucao["Var_Total"] = df_evolucao["Estoque Total"].diff()

    def seta_total(v):
        if pd.isna(v):
            return ""
        if v > 0:
            return "🟢⬆️"
        if v < 0:
            return "🔴⬇️"
        return "⚪"

    df_evolucao["Δ Estoque"] = df_evolucao["Var_Total"].apply(seta_total)

    # ==========================================
    # CALCULAR VARIAÇÃO DO OBSOLETO
    # ==========================================

    df_evolucao["Var_Obs"] = df_evolucao["Estoque Obsoleto"].diff()

    def seta_obs(v):
        if pd.isna(v):
            return ""
        if v > 0:
            return "🔴⬆️"
        if v < 0:
            return "🟢⬇️"
        return "⚪"

    df_evolucao["Δ Obsoleto"] = df_evolucao["Var_Obs"].apply(seta_obs)

    # ==========================================
    # FORMATAÇÃO DOS VALORES
    # ==========================================

    df_evolucao["Estoque Total"] = df_evolucao["Estoque Total"].apply(moeda_br)

    df_evolucao["Estoque Obsoleto"] = df_evolucao["Estoque Obsoleto"].apply(moeda_br)

    df_evolucao["% Obsoleto"] = (
        df_evolucao["% Obsoleto"] * 100
    ).round(2).astype(str) + "%"

    # ==========================================
    # ORDEM DAS COLUNAS
    # ==========================================

    df_evolucao = df_evolucao[
        [
            "Data Fechamento",
            "Estoque Total",
            "Δ Estoque",
            "Estoque Obsoleto",
            "Δ Obsoleto",
            "% Obsoleto",
        ]
    ]

    # ==========================================
    # TABELA
    # ==========================================

    st.dataframe(
        df_evolucao,
        use_container_width=True,
        hide_index=True
    )
