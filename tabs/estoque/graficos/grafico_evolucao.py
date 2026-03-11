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

    # -------------------------------------------------
    # COLUNAS CALENDÁRIO
    # -------------------------------------------------

    evolucao["Ano"] = evolucao["Data Fechamento"].dt.year
    evolucao["Mes"] = evolucao["Data Fechamento"].dt.month

    evolucao["AnoMes"] = evolucao["Ano"] * 100 + evolucao["Mes"]

    evolucao["AnoMesLabel"] = evolucao["Data Fechamento"].dt.strftime("%y-%b").str.lower()

    # -------------------------------------------------
    # LABEL DOS VALORES
    # -------------------------------------------------

    evolucao["Label"] = evolucao["Custo Total"].apply(
        lambda x: f"R$ {x/1_000_000:.1f} Mi"
    )

    # -------------------------------------------------
    # BASE DO GRÁFICO
    # -------------------------------------------------

    base = alt.Chart(evolucao).encode(

        x=alt.X(
            "AnoMesLabel:N",
            sort=alt.SortField(field="AnoMes", order="ascending"),
            axis=alt.Axis(
                title=None,
                labelAngle=0,
                labelColor="white",
                labelFontSize=11
            )
        ),

        y=alt.Y(
            "Custo Total:Q",
            axis=None
        )
    )

    # -------------------------------------------------
    # AREA
    # -------------------------------------------------

    area = base.mark_area(
        opacity=0.35,
        color="#ff7f0e"
    )

    # -------------------------------------------------
    # LINHA
    # -------------------------------------------------

    line = base.mark_line(
        color="#ff7f0e",
        strokeWidth=3
    )

    # -------------------------------------------------
    # PONTOS
    # -------------------------------------------------

    points = base.mark_circle(
        size=70,
        color="#ff7f0e"
    )

    # -------------------------------------------------
    # LABELS DOS VALORES
    # -------------------------------------------------

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