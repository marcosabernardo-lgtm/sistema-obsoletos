import streamlit as st
import pandas as pd
from analytics.analises import evolucao_estoque


def render(df_kpi, moeda_br):

    df_evolucao = evolucao_estoque(df_kpi)

    # ==========================================
    # DATA
    # ==========================================

    df_evolucao["Data Fechamento"] = pd.to_datetime(
        df_evolucao["Data Fechamento"]
    ).dt.date

    # ==========================================
    # VARIAÇÃO ESTOQUE TOTAL
    # ==========================================

    df_evolucao["Var_Total"] = df_evolucao["Estoque Total"].diff()

    def delta_total(v):

        if pd.isna(v):
            return ""

        valor = moeda_br(abs(v))

        if v > 0:
            return f"🟢 ⬆ +{valor}"
        elif v < 0:
            return f"🔴 ⬇ -{valor}"

        return ""

    df_evolucao["Δ Estoque"] = df_evolucao["Var_Total"].apply(delta_total)

    # ==========================================
    # VARIAÇÃO OBSOLETO
    # ==========================================

    df_evolucao["Var_Obs"] = df_evolucao["Estoque Obsoleto"].diff()

    def delta_obs(v):

        if pd.isna(v):
            return ""

        valor = moeda_br(abs(v))

        if v > 0:
            return f"🔴 ⬆ +{valor}"
        elif v < 0:
            return f"🟢 ⬇ -{valor}"

        return ""

    df_evolucao["Δ Obsoleto"] = df_evolucao["Var_Obs"].apply(delta_obs)

    # ==========================================
    # VARIAÇÃO % OBSOLETO
    # ==========================================

    df_evolucao["Var_Percent"] = df_evolucao["% Obsoleto"].diff()

    def delta_percent(v):

        if pd.isna(v):
            return ""

        valor = round(abs(v * 100), 2)

        if v > 0:
            return f" 🔴 ⬆ +{valor}%"
        elif v < 0:
            return f" 🟢 ⬇ -{valor}%"

        return ""

    df_evolucao["Δ Percent"] = df_evolucao["Var_Percent"].apply(delta_percent)

    # ==========================================
    # FORMATAÇÃO DOS VALORES
    # ==========================================

    df_evolucao["Estoque Total"] = df_evolucao["Estoque Total"].apply(moeda_br)

    df_evolucao["Estoque Obsoleto"] = df_evolucao["Estoque Obsoleto"].apply(moeda_br)

    df_evolucao["% Obsoleto"] = (
        (df_evolucao["% Obsoleto"] * 100).round(2).astype(str) + "%"
        + df_evolucao["Δ Percent"]
    )

    # ==========================================
    # ORDEM FINAL DAS COLUNAS
    # ==========================================

    df_evolucao = df_evolucao[
        [
            "Data Fechamento",
            "Estoque Total",
            "Δ Estoque",
            "Estoque Obsoleto",
            "Δ Obsoleto",
            "% Obsoleto"
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
