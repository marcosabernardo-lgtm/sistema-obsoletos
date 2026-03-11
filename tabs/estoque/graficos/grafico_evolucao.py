import streamlit as st
import pandas as pd
import altair as alt


def render(df):

    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"])

    evolucao = (
        df.groupby("Data Fechamento")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Data Fechamento")
    )

    evolucao["Label"] = evolucao["Custo Total"].apply(
        lambda x: f"R$ {x/1_000_000:.1f} Mi"
    )

    base = alt.Chart(evolucao).encode(
        x=alt.X("Data Fechamento:T", title="Fechamento"),
        y=alt.Y("Custo Total:Q", title="Valor Estoque")
    )

    area = base.mark_area(
        opacity=0.35,
        color="#ff7f0e"
    )

    line = base.mark_line(
        color="#ff7f0e",
        strokeWidth=3
    )

    points = base.mark_circle(
        size=60,
        color="#ff7f0e"
    )

    labels = base.mark_text(
        dy=-10,
        fontSize=11
    ).encode(
        text="Label"
    )

    chart = area + line + points + labels

    st.altair_chart(chart, use_container_width=True)