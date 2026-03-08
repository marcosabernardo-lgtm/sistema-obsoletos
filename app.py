import streamlit as st
import pandas as pd
import os
from datetime import datetime

from motor.motor_obsoletos import executar_motor
from motor.motor_estoque import executar_motor_estoque

from storage.base_obsoletos_lake import salvar_fechamento_obsoletos
from storage.base_estoque_lake import salvar_fechamento_estoque


st.set_page_config(page_title="Upload Estoque", layout="wide")

# ---------------------------------------------------------
# GARANTIR ESTRUTURA DE PASTAS
# ---------------------------------------------------------

os.makedirs("data", exist_ok=True)
os.makedirs("data/obsoletos", exist_ok=True)
os.makedirs("data/estoque", exist_ok=True)
os.makedirs("data/uploads", exist_ok=True)

LOG_PATH = "data/log_uploads.parquet"
UPLOAD_DIR = "data/uploads"


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


# ---------------------------------------------------------
# FUNÇÕES DE LOG
# ---------------------------------------------------------

def carregar_log():

    if os.path.exists(LOG_PATH):
        return pd.read_parquet(LOG_PATH)

    return pd.DataFrame(columns=["Arquivo", "Data", "Registros", "Tipo"])


def salvar_log(nome_zip, registros, tipo):

    df_log = carregar_log()

    from datetime import timezone, timedelta

    agora = datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=-3))
    )

    novo = pd.DataFrame([{
        "Arquivo": nome_zip,
        "Data": agora,
        "Registros": registros,
        "Tipo": tipo
    }])

    df_log = pd.concat([df_log, novo], ignore_index=True)

    df_log.to_parquet(LOG_PATH, index=False)

    return df_log


# ---------------------------------------------------------
# HISTÓRICO
# ---------------------------------------------------------

def mostrar_historico():

    df_log = carregar_log()

    if len(df_log) > 0:

        df_view = df_log.sort_values("Data", ascending=False).copy()

        df_view["Data"] = pd.to_datetime(df_view["Data"]).dt.strftime("%d/%m/%Y")

        st.subheader("📂 Arquivos já importados")

        st.dataframe(df_view, use_container_width=True, hide_index=True)

    else:

        st.info("Nenhum arquivo importado ainda.")


mostrar_historico()

st.markdown("---")


# ---------------------------------------------------------
# RESET
# ---------------------------------------------------------

with st.expander("⚠️ Zona de Perigo — Resetar Base"):

    if st.button("🗑 Resetar tudo"):

        import shutil

        if os.path.exists("data"):
            shutil.rmtree("data")

        st.success("Bases removidas")

        st.rerun()

st.markdown("---")


# ---------------------------------------------------------
# STATUS DO DATA LAKE
# ---------------------------------------------------------

with st.expander("📊 Status da Base de Dados"):

    st.write("Arquivos em obsoletos:", os.listdir("data/obsoletos"))
    st.write("Arquivos em estoque:", os.listdir("data/estoque"))


# ---------------------------------------------------------
# TIPO PROCESSAMENTO
# ---------------------------------------------------------

st.subheader("Tipo de processamento")

tipo_processo = st.radio(
    "Escolha o tipo de processamento",
    [
        "Atualizar Obsolescência",
        "Atualizar Evolução de Estoque"
    ]
)

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

    caminho_upload = os.path.join(UPLOAD_DIR, nome_zip)

    st.write("Arquivo selecionado:", nome_zip)

    df_log = carregar_log()

    if nome_zip in df_log["Arquivo"].values:

        st.error("⚠ Este arquivo já foi importado anteriormente.")
        st.stop()

    if st.button("🚀 Processar Arquivo"):

        with st.spinner("Processando arquivo..."):

            try:

                # -------------------------------------------------
                # SALVAR ZIP EM DISCO
                # -------------------------------------------------

                with open(caminho_upload, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # -------------------------------------------------
                # PROCESSAMENTO
                # -------------------------------------------------

                if tipo_processo == "Atualizar Obsolescência":

                    df_final, df_export = executar_motor(caminho_upload)

                    caminho = salvar_fechamento_obsoletos(df_final)

                    tipo = "Obsolescência"

                else:

                    df_final, df_export = executar_motor_estoque(caminho_upload)

                    caminho = salvar_fechamento_estoque(df_final)

                    tipo = "Evolução Estoque"

                qtd_registros = len(df_final)

                salvar_log(nome_zip, qtd_registros, tipo)

                st.success("✅ Processamento concluído!")

                st.rerun()

                st.write("Arquivo salvo em:", caminho)

                st.write("Registros:", qtd_registros)

                st.download_button(
                    label="📥 Baixar Excel Final",
                    data=df_export,
                    file_name=f"{nome_zip.replace('.zip','')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:

                st.error("Erro inesperado durante o processamento.")
                st.exception(e)