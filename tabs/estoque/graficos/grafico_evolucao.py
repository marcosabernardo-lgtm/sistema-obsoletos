import streamlit as st
import pandas as pd
import altair as alt


def render(df):

    df = df.copy()

    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"])

    evolucao = (
        df.groupby("Data Fechamento")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Data Fechamento")
    )

    # -----------------------------
    # calendário estilo Power BI
    # -----------------------------

    evolucao["Ano"] = evolucao["Data Fechamento"].dt.year
    evolucao["Mes"] = evolucao["Data Fechamento"].dt.month
    evolucao["AnoMes"] = evolucao["Ano"] * 100 + evolucao["Mes"]

    evolucao["AnoMesLabel"] = evolucao["Data Fechamento"].dt.strftime("%y-%b").str.lower()

    # -----------------------------
    # label dos valores
    # -----------------------------

    evolucao["Label"] = evolucao["Custo Total"].apply(
        lambda x: f"R$ {x/1_000_000:.1f} Mi"
    )

    # -----------------------------
    # base
    # -----------------------------

    base = alt.Chart(evolucao).encode(

        x=alt.X(
            "AnoMesLabel:N",
            sort=alt.SortField(field="AnoMes"),
            axis=alt.Axis(
                title=None,
                labelAngle=0,
                labelColor="white",
                labelFontSize=11,
                tickSize=0
            )
        ),

        y=alt.Y(
            "Custo Total:Q",
            axis=None   # remove eixo Y completamente
        )
    )

    # -----------------------------
    # area
    # -----------------------------

    area = base.mark_area(
        opacity=0.35,
        color="#ff7f0e"
    )

    # -----------------------------
    # linha
    # -----------------------------

    line = base.mark_line(
        color="#ff7f0e",
        strokeWidth=3
    )

    # -----------------------------
    # pontos
    # -----------------------------

    points = base.mark_circle(
        size=70,
        color="#ff7f0e"
    )

    # -----------------------------
    # labels
    # -----------------------------

    labels = base.mark_text(
        dy=-12,
        fontSize=11,
        color="white"
    ).encode(
        text="Label"
    )

    chart = (area + line + points + labels).properties(
        height=420
    )

    st.altair_chart(chart, use_container_width=True)