import streamlit as st
import pandas as pd
from motor_obsoletos import executar_motor
from base_historica import atualizar_base_historica

st.set_page_config(page_title="Sistema de Obsoletos", layout="wide")

st.title("📦 Sistema de Controle de Obsoletos")

st.markdown("---")

st.subheader("Upload do Arquivo")

uploaded_file = st.file_uploader(
    "Selecione o arquivo PROJETO_UPLOAD.zip",
    type=["zip"]
)

if uploaded_file is not None:

    if st.button("🚀 Processar Arquivo"):

        st.info("Processando arquivo...")

        df_final, df_export = executar_motor(uploaded_file)

        if df_final is not None:

            # salva no histórico
            df_hist = atualizar_base_historica(df_final)

            st.success("Processamento concluído com sucesso!")

            st.write("Registros no histórico:", len(df_hist))

            st.subheader("Base Processada")

            st.dataframe(df_final)

            st.download_button(
                label="📥 Baixar Excel Final",
                data=df_export,
                file_name="Base_Obsoletos_Final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.markdown("---")

            st.subheader("📚 Base Histórica Acumulada")

            st.dataframe(df_hist)

        else:

            st.error("Erro no processamento.")
