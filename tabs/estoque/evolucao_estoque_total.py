import streamlit as st
import pandas as pd
import altair as alt


def render(df):

    st.subheader("Evolução do Estoque Total")

    # Agrupar por data
    df_evol = (
        df.groupby("Data Fechamento")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Data Fechamento")
    )

    # Gráfico
    chart = (
        alt.Chart(df_evol)
        .mark_line(point=True)
        .encode(
            x="Data Fechamento:T",
            y="Custo Total:Q",
            tooltip=["Data Fechamento", "Custo Total"]
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)

    # Tabela
    st.dataframe(
        df_evol,
        use_container_width=True,
        hide_index=True
    )