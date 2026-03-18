import streamlit as st
import pandas as pd
import altair as alt


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


def render(df, modo, moeda_br):

    st.subheader(f"Distribuição por Faixa DIO — {modo}")

    col_a, col_b = st.columns(2)

    df_dist = (
        df.groupby("Faixa_calc", as_index=False)
        .agg(Itens=("Produto", "count"), Custo=("Custo Total", "sum"))
        .rename(columns={"Faixa_calc": "Faixa DIO"})
    )
    df_dist["Faixa DIO"] = pd.Categorical(df_dist["Faixa DIO"], categories=ORDEM_FAIXAS, ordered=True)
    df_dist = df_dist.sort_values("Faixa DIO")

    with col_a:
        st.markdown("**Quantidade de Itens por Faixa**")
        st.altair_chart(
            alt.Chart(df_dist)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Faixa DIO:N", sort=ORDEM_FAIXAS, title="Faixa DIO",
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                y=alt.Y("Itens:Q", title="Qtd Itens",
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                color=alt.Color("Faixa DIO:N",
                                scale=alt.Scale(domain=list(CORES_FAIXAS.keys()),
                                                range=list(CORES_FAIXAS.values())),
                                legend=None),
                tooltip=["Faixa DIO", "Itens"]
            )
            .properties(height=350, background="transparent")
            .configure_view(strokeOpacity=0)
            .configure_axis(gridColor="#1a6b72"),
            use_container_width=True
        )

    with col_b:
        st.markdown("**Valor (Custo Total) por Faixa**")
        st.altair_chart(
            alt.Chart(df_dist)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Faixa DIO:N", sort=ORDEM_FAIXAS, title="Faixa DIO",
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                y=alt.Y("Custo:Q", title="Custo Total (R$)",
                        axis=alt.Axis(labelColor="white", titleColor="white", format=",.0f")),
                color=alt.Color("Faixa DIO:N",
                                scale=alt.Scale(domain=list(CORES_FAIXAS.keys()),
                                                range=list(CORES_FAIXAS.values())),
                                legend=None),
                tooltip=["Faixa DIO", alt.Tooltip("Custo:Q", format=",.2f", title="Custo R$")]
            )
            .properties(height=350, background="transparent")
            .configure_view(strokeOpacity=0)
            .configure_axis(gridColor="#1a6b72"),
            use_container_width=True
        )

    st.markdown("**Distribuição por Empresa / Filial**")
    df_emp = (
        df.groupby(["Empresa / Filial", "Faixa_calc"], as_index=False)
        .agg(Itens=("Produto", "count"))
        .rename(columns={"Faixa_calc": "Faixa DIO"})
    )
    df_emp["Faixa DIO"] = pd.Categorical(df_emp["Faixa DIO"], categories=ORDEM_FAIXAS, ordered=True)
    df_pivot = (
        df_emp.pivot_table(
            index="Empresa / Filial", columns="Faixa DIO",
            values="Itens", aggfunc="sum", fill_value=0
        ).reset_index()
    )
    cols_pres = ["Empresa / Filial"] + [f for f in ORDEM_FAIXAS if f in df_pivot.columns]
    st.dataframe(df_pivot[cols_pres], use_container_width=True, hide_index=True)
