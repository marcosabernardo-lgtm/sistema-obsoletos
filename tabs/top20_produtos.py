import streamlit as st
import pandas as pd


def render(df_filtrado, moeda_br):

    ultima_data = df_filtrado["Data Fechamento"].max()

    base = df_filtrado[df_filtrado["Data Fechamento"] == ultima_data]

    top20 = (
        base
        .groupby(
            ["Empresa / Filial", "Conta", "Produto", "Descricao"],
            as_index=False
        )
        .agg(
            Quantidade=("Saldo Atual", "sum"),
            Custo_Total=("Custo Total", "sum")
        )
    )

    # calcular percentual
    total_geral = top20["Custo_Total"].sum()
    top20["%"] = (top20["Custo_Total"] / total_geral) * 100

    # ordenar
    top20 = (
        top20
        .sort_values("Custo_Total", ascending=False)
        .head(20)
    )

    # ranking
    top20.insert(0, "Ranking", range(1, len(top20) + 1))

    # renomear
    top20 = top20.rename(columns={"Custo_Total": "Custo Total"})

    # formatar
    top20["Custo Total"] = top20["Custo Total"].apply(moeda_br)
    top20["%"] = top20["%"].apply(lambda x: f"{x:.2f}%")

    # ordem das colunas
    top20 = top20[
        [
            "Ranking",
            "Empresa / Filial",
            "Conta",
            "Produto",
            "Descricao",
            "Quantidade",
            "Custo Total",
            "%"
        ]
    ]

    st.dataframe(
        top20,
        use_container_width=True,
        hide_index=True
    )
