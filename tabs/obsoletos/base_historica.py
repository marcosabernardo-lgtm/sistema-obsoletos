import streamlit as st
import pandas as pd


def render(df_filtrado, moeda_br):

    base = df_filtrado.copy()

    base["Data Fechamento"] = pd.to_datetime(
        base["Data Fechamento"]
    ).dt.date

    if "Vlr Unit" in base.columns:
        base["Vlr Unit"] = pd.to_numeric(base["Vlr Unit"], errors="coerce").apply(
            lambda x: moeda_br(x) if pd.notna(x) else ""
        )

    base["Custo Total"] = base["Custo Total"].apply(moeda_br)

    st.dataframe(
        base,
        use_container_width=True,
        hide_index=True
    )