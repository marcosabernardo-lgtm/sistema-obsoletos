import streamlit as st
import pandas as pd
import altair as alt


def render(df, moeda_br):

    st.subheader("Evolução do Estoque Total")

    # -------------------------------------------------
    # AGRUPAMENTO
    # -------------------------------------------------

    df_evol = (
        df
        .groupby("Data Fechamento")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Data Fechamento")
    )

    # -------------------------------------------------
    # FORMATAÇÃO
    # -------------------------------------------------

    df_evol["Estoque Total"] = df_evol["Custo Total"].apply(moeda_br)

    # -------------------------------------------------
    # GRÁFICO
    # -------------------------------------------------

    chart = (
        alt.Chart(df_evol)
        .mark_line(point=True)
        .encode(
            x="Data Fechamento:T",
            y="Custo Total:Q",
            tooltip=["Data Fechamento", "Estoque Total"]
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)

    # -------------------------------------------------
    # TABELA
    # -------------------------------------------------

    st.dataframe(
        df_evol[["Data Fechamento", "Estoque Total"]],
        use_container_width=True,
        hide_index=True
    )