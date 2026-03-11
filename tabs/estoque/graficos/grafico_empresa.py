import streamlit as st
import pandas as pd
import altair as alt


def render(df, moeda_br):
    df = df.copy()
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"])

    ultima_data = df["Data Fechamento"].max()
    base = df[df["Data Fechamento"] == ultima_data]

    empresa = (
        base.groupby("Empresa / Filial")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Custo Total", ascending=False)
    )

    empresa["Label"] = empresa["Custo Total"].apply(
        lambda x: f"R$ {x/1_000_000:.1f} Mi" if x >= 1_000_000 else f"R$ {x/1_000:.0f} Mil"
    )

    bars = alt.Chart(empresa).mark_bar(
        color="#ff7f0e",
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4
    ).encode(
        x=alt.X(
            "Empresa / Filial:N",
            sort=alt.SortField(field="Custo Total", order="descending"),
            axis=alt.Axis(
                title=None,
                labelAngle=0,
                labelColor="white",
                labelFontSize=11,
                tickColor="white",
                domainColor="white"
            )
        ),
        y=alt.Y(
            "Custo Total:Q",
            axis=alt.Axis(
                title=None,
                labels=False,
                ticks=False,
                grid=False,
                domain=False
            )
        ),
        tooltip=[
            alt.Tooltip("Empresa / Filial:N", title="Empresa"),
            alt.Tooltip("Custo Total:Q", title="Valor", format=",.2f")
        ]
    )

    labels = alt.Chart(empresa).mark_text(
        dy=-10,
        color="white",
        fontSize=11
    ).encode(
        x=alt.X(
            "Empresa / Filial:N",
            sort=alt.SortField(field="Custo Total", order="descending")
        ),
        y=alt.Y("Custo Total:Q"),
        text="Label"
    )

    chart = (bars + labels).properties(
        height=420
    ).configure_view(
        strokeWidth=0
    ).configure_axisX(
        grid=False,
        labelColor="white",
        labelAngle=0,
        tickColor="white",
        domainColor="white"
    ).configure_axisY(
        grid=False,
        labels=False,
        ticks=False,
        domain=False,
        title=None
    )

    st.altair_chart(chart, use_container_width=True)