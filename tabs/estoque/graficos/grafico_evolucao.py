import streamlit as st
import pandas as pd
import altair as alt


def render(df):

    # -------------------------------------------------
    # BASE
    # -------------------------------------------------

    df = df.copy()

    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"])

    evolucao = (
        df.groupby("Data Fechamento")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Data Fechamento")
    )

    # -------------------------------------------------
    # COLUNAS CALENDÁRIO (MESMO CONCEITO DO POWER BI)
    # -------------------------------------------------

    evolucao["Ano"] = evolucao["Data Fechamento"].dt.year
    evolucao["Mes"] = evolucao["Data Fechamento"].dt.month

    evolucao["AnoMes"] = evolucao["Ano"] * 100 + evolucao["Mes"]

    evolucao["AnoMesLabel"] = evolucao["Data Fechamento"].dt.strftime("%y-%b").str.lower()

    # -------------------------------------------------
    # LABEL DO VALOR
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
            title="Fechamento",
            sort=alt.SortField(
                field="AnoMes",
                order="ascending"
            )
        ),

        y=alt.Y(
            "Custo Total:Q",
            title="Valor Estoque"
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
    # LABELS
    # -------------------------------------------------

    labels = base.mark_text(
        dy=-12,
        fontSize=11
    ).encode(
        text="Label"
    )

    chart = area + line + points + labels

    st.altair_chart(chart, use_container_width=True)