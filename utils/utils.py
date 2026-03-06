import streamlit as st
import pandas as pd
import io


def dataframe_para_excel(df):

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    output.seek(0)

    return output


def botao_download_excel(df, nome_arquivo):

    excel = dataframe_para_excel(df)

    st.download_button(
        label="📥 Exportar para Excel",
        data=excel,
        file_name=nome_arquivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )