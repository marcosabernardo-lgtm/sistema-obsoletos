import streamlit as st
import pandas as pd


def render(df_filtrado, moeda_br):

    ultima_data = df_filtrado["Data Fechamento"].max()

    top20 = (
        df_filtrado[df_filtrado["Data Fechamento"] == ultima_data]
        .groupby(["Empresa / Filial", "Produto", "Descricao"], as_index=False)
        .agg(
            Quantidade=("Saldo Atual", "sum"),
            Custo_Total=("Custo Total", "sum")
        )
        .sort_values("Custo_Total", ascending=False)
        .head(20)
    )

    top20.insert(0, "Ranking", range(1, len(top20) + 1))

    top20 = top20.rename(columns={"Custo_Total": "Custo Total"})

    top20["Custo Total"] = top20["Custo Total"].apply(moeda_br)

    st.dataframe(
        top20,
        use_container_width=True,
        hide_index=True
    )
