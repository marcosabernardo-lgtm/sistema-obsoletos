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

    evolucao["Ano"] = evolucao["Data Fechamento"].dt.year
    evolucao["Mes"] = evolucao["Data Fechamento"].dt.month
    evolucao["AnoMes"] = evolucao["Ano"] * 100 + evolucao["Mes"]
    evolucao["AnoMesLabel"] = evolucao["Data Fechamento"].dt.strftime("%y-%b").str.lower()

    evolucao["Label"] = evolucao["Custo Total"].apply(
        lambda x: f"R$ {x/1_000_000:.1f} Mi"
    )

    base = alt.Chart(evolucao).encode(
        x=alt.X(
            "AnoMesLabel:N",
            sort=alt.SortField(field="AnoMes"),
            axis=alt.Axis(
                title=None,
                labelAngle=0,
                labelColor="white",
                labelFontSize=11,
                grid=False,
                tickColor="white",
                domainColor="white"
            )
        ),
        y=alt.Y(
            "Custo Total:Q",
            axis=None
        )
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
        size=70,
        color="#ff7f0e"
    )

    labels = base.mark_text(
        dy=-12,
        color="white",
        fontSize=11
    ).encode(
        text="Label"
    )

    chart = (
        area + line + points + labels
    ).properties(
        height=420
    ).configure_view(
        strokeWidth=0
    ).configure_axisX(
        grid=False,
        labelColor="white",
        labelAngle=0,
        tickColor="white",
        domainColor="white"
    )

    st.altair_chart(chart, use_container_width=True)