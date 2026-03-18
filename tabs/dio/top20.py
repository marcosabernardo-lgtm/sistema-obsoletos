import streamlit as st
import altair as alt
import numpy as np


ORDEM_FAIXAS = [
    "Até 30 dias",
    "31–90 dias",
    "91–180 dias",
    "181–365 dias",
    "+ 1 ano",
    "Sem consumo"
]

CORES_FAIXAS = {
    "Até 30 dias":   "#2ecc71",
    "31–90 dias":    "#f1c40f",
    "91–180 dias":   "#e67e22",
    "181–365 dias":  "#e74c3c",
    "+ 1 ano":       "#8e44ad",
    "Sem consumo":   "#7f8c8d"
}


def render(df, modo, label_eixo, label_consumo, moeda_br):

    st.subheader(f"Top 20 — Maior DIO {modo} (excluindo 'Sem consumo')")

    df_top = (
        df[df["DIO_calc"] != np.inf]
        .nlargest(20, "DIO_calc")
        [["Empresa / Filial", "Produto", "Descricao",
          "Saldo Atual", "Custo Total", "Consumo_exib",
          "DIO_calc", "DIO_fmt_calc", "Faixa_calc"]]
        .copy()
        .rename(columns={
            "DIO_calc":     "DIO",
            "DIO_fmt_calc": "Tempo DIO",
            "Faixa_calc":   "Faixa DIO",
            "Consumo_exib": label_consumo,
        })
    )

    if df_top.empty:
        st.info("Nenhum produto com DIO calculado para os filtros selecionados.")
        return

    df_top_chart = df_top.copy()
    df_top_chart["Label"] = df_top_chart["Produto"] + " — " + df_top_chart["Descricao"].str[:30]

    st.altair_chart(
        alt.Chart(df_top_chart)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#EC6E21")
        .encode(
            y=alt.Y("Label:N", sort="-x", title=None,
                    axis=alt.Axis(labelColor="white", labelLimit=300)),
            x=alt.X("DIO:Q", title=label_eixo,
                    axis=alt.Axis(labelColor="white", titleColor="white")),
            tooltip=["Empresa / Filial", "Produto", "Descricao",
                     alt.Tooltip("DIO:Q", format=".0f", title=label_eixo),
                     "Tempo DIO", "Faixa DIO"]
        )
        .properties(height=500, background="transparent")
        .configure_view(strokeOpacity=0)
        .configure_axis(gridColor="#1a6b72"),
        use_container_width=True
    )

    df_top_display = df_top.copy()
    df_top_display["Custo Total"] = df_top_display["Custo Total"].apply(moeda_br)
    df_top_display["DIO"] = df_top_display["DIO"].apply(lambda x: f"{x:.1f}")
    st.dataframe(df_top_display, use_container_width=True, hide_index=True)
