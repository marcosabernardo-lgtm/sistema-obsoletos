import streamlit as st
import pandas as pd


def render(df_filtrado, moeda_br):

    base = df_filtrado.copy()

    base["Data Fechamento"] = pd.to_datetime(
        base["Data Fechamento"]
    ).dt.date

    base["Custo Total"] = base["Custo Total"].apply(moeda_br)

    st.dataframe(
        base,
        use_container_width=True,
        hide_index=True
    )
