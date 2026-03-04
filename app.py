import streamlit as st
import pandas as pd

from motor_obsoletos import executar_motor
from base_historica import atualizar_base_historica
from analises import evolucao_estoque

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

            df_hist = atualizar_base_historica(df_final)

            st.success("Processamento concluído com sucesso!")

            st.write("Registros no histórico:", len(df_hist))

            st.markdown("---")

            st.subheader("Base Processada")

            # tirar horas da data
            df_final["Data Fechamento"] = pd.to_datetime(df_final["Data Fechamento"]).dt.date

            st.dataframe(df_final)

            st.download_button(
                label="📥 Baixar Excel Final",
                data=df_export,
                file_name="Base_Obsoletos_Final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.markdown("---")

            st.subheader("📚 Base Histórica Acumulada")

            df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"]).dt.date

            st.dataframe(df_hist)

            st.markdown("---")

            st.subheader("📊 Evolução do Estoque")

            df_evolucao = evolucao_estoque(df_hist)

            df_evolucao["Data Fechamento"] = pd.to_datetime(df_evolucao["Data Fechamento"]).dt.date

            # formatação monetária
            df_evolucao["Estoque Total"] = df_evolucao["Estoque Total"].map(lambda x: f"R$ {x:,.2f}")
            df_evolucao["Estoque Obsoleto"] = df_evolucao["Estoque Obsoleto"].map(lambda x: f"R$ {x:,.2f}")

            # percentual
            df_evolucao["% Obsoleto"] = (df_evolucao["% Obsoleto"] * 100).map(lambda x: f"{x:.2f}%")

            st.dataframe(df_evolucao)

            # gráfico continua usando valores originais
            df_chart = evolucao_estoque(df_hist)

            st.line_chart(
                df_chart.set_index("Data Fechamento")[
                    ["Estoque Total", "Estoque Obsoleto"]
                ]
            )

        else:

            st.error("Erro no processamento.")
