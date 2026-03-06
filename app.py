import streamlit as st
import pandas as pd
import os
from datetime import datetime

from motor_obsoletos import executar_motor
from base_historica import atualizar_base_historica


st.set_page_config(page_title="Upload Estoque", layout="wide")

st.title("📦 Upload de Fechamento de Estoque")

st.markdown(
"""
Faça o upload do arquivo **PROJETO_UPLOAD.zip** contendo as bases do ERP.

O sistema irá:

• Processar o estoque  
• Calcular movimentações  
• Classificar obsolescência  
• Atualizar a base histórica
"""
)

st.markdown("---")

BASE_PATH = "data/base_historica.parquet"
LOG_PATH  = "data/log_uploads.parquet"


# ---------------------------------------------------------
# FUNÇÕES DE LOG
# ---------------------------------------------------------

def carregar_log():
    if os.path.exists(LOG_PATH):
        return pd.read_parquet(LOG_PATH)
    return pd.DataFrame(columns=["Arquivo", "Data", "Hora", "Registros"])


def salvar_log(nome_zip, registros):
    df_log = carregar_log()
    agora = datetime.now()
    novo = pd.DataFrame([{
        "Arquivo":   nome_zip,
        "Data":      agora.strftime("%d/%m/%Y"),
        "Hora":      agora.strftime("%H:%M:%S"),
        "Registros": registros
    }])
    df_log = pd.concat([df_log, novo], ignore_index=True)
    os.makedirs("data", exist_ok=True)
    df_log.to_parquet(LOG_PATH, index=False)
    return df_log


# ---------------------------------------------------------
# MOSTRAR HISTÓRICO DE UPLOADS
# ---------------------------------------------------------

def mostrar_historico():
    df_log = carregar_log()
    if len(df_log) > 0:
        st.subheader("📂 Arquivos já importados")
        st.dataframe(
            df_log.sort_values("Data", ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhum arquivo importado ainda.")


mostrar_historico()

st.markdown("---")

# ---------------------------------------------------------
# ZONA DE PERIGO — RESET DA BASE
# ---------------------------------------------------------

with st.expander("⚠️ Zona de Perigo — Resetar Base"):
    st.warning("Isso irá deletar toda a base histórica e o log de uploads. Use com cuidado!")
    if st.button("🗑 Deletar base histórica e log"):
        deletados = []
        for path in [BASE_PATH, LOG_PATH]:
            if os.path.exists(path):
                os.remove(path)
                deletados.append(path)
        if deletados:
            st.success(f"Deletado: {', '.join(deletados)}")
        else:
            st.info("Nenhum arquivo encontrado para deletar.")
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# UPLOAD
# ---------------------------------------------------------

uploaded_file = st.file_uploader(
    "Selecione o arquivo PROJETO_UPLOAD.zip",
    type=["zip"]
)

if uploaded_file is not None:

    nome_zip = uploaded_file.name

    st.write("Arquivo selecionado:", nome_zip)

    # ---------------------------------------------------------
    # BLOQUEAR DUPLICIDADE
    # ---------------------------------------------------------

    df_log = carregar_log()

    if nome_zip in df_log["Arquivo"].values:
        st.error("⚠ Este arquivo já foi importado anteriormente.")
        st.stop()

    # ---------------------------------------------------------
    # PROCESSAR
    # ---------------------------------------------------------

    if st.button("🚀 Processar Arquivo"):

        with st.spinner("Processando arquivo..."):

            try:

                df_final, df_export = executar_motor(uploaded_file)

                if df_final is not None:

                    df_final["arquivo_upload"] = nome_zip

                    df_hist = atualizar_base_historica(df_final)

                    df_log = salvar_log(nome_zip, len(df_hist))

                    st.success("✅ Processamento concluído!")
                    st.write("Registros no histórico:", len(df_hist))

                    st.markdown("---")
                    st.subheader("📂 Arquivos importados")
                    st.dataframe(
                        df_log.sort_values("Data", ascending=False),
                        use_container_width=True,
                        hide_index=True
                    )

                    st.download_button(
                        label="📥 Baixar Excel Final",
                        data=df_export,
                        file_name=f"{nome_zip.replace('.zip','')}_obsoletos.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                else:
                    st.error("Erro no processamento.")

            except Exception as e:
                st.error("Erro inesperado durante o processamento.")
                st.exception(e)