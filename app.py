import streamlit as st
import pandas as pd
import os
from datetime import datetime

from motor.motor_obsoletos import executar_motor
from motor.motor_estoque import executar_motor_estoque

from storage.base_obsoletos_lake import salvar_fechamento_obsoletos
from storage.base_estoque_lake import salvar_fechamento_estoque


st.set_page_config(page_title="Processamento de Estoque", layout="wide")


# ---------------------------------------------------------
# GARANTIR ESTRUTURA DE PASTAS
# ---------------------------------------------------------

os.makedirs("data", exist_ok=True)
os.makedirs("data/obsoletos", exist_ok=True)
os.makedirs("data/estoque", exist_ok=True)

LOG_PATH = "data/log_uploads.parquet"


st.title("📊 Dashboard de Estoque e Obsolescência")

st.markdown(
"""
Este painel apresenta análises consolidadas do estoque da empresa com base nos fechamentos mensais do ERP.

As informações incluem:

• Evolução do valor total em estoque  
• Identificação de itens obsoletos  
• Classificação por tempo sem movimentação  
• Distribuição por empresa e filial
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
# RESET
# ---------------------------------------------------------

with st.expander("⚠️ Zona de Perigo — Resetar Base"):

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        if st.button("🗑 Resetar Estoque"):
            import shutil
            if os.path.exists("data/estoque"):
                shutil.rmtree("data/estoque")
                os.makedirs("data/estoque", exist_ok=True)
            if os.path.exists(LOG_PATH):
                df_log = carregar_log()
                df_log = df_log[df_log["Tipo"] != "Evolução Estoque"]
                df_log.to_parquet(LOG_PATH, index=False)
            st.success("Base de estoque resetada.")
            st.cache_data.clear()
            st.rerun()

    with col_r2:
        if st.button("🗑 Resetar Obsoletos"):
            import shutil
            if os.path.exists("data/obsoletos"):
                shutil.rmtree("data/obsoletos")
                os.makedirs("data/obsoletos", exist_ok=True)
            if os.path.exists(LOG_PATH):
                df_log = carregar_log()
                df_log = df_log[df_log["Tipo"] != "Obsolescência"]
                df_log.to_parquet(LOG_PATH, index=False)
            st.success("Base de obsoletos resetada.")
            st.cache_data.clear()
            st.rerun()

    with col_r3:
        if st.button("🗑 Resetar Tudo"):
            import shutil
            if os.path.exists("data"):
                shutil.rmtree("data")
            st.success("Todas as bases removidas.")
            st.cache_data.clear()
            st.rerun()


st.markdown("---")


# ---------------------------------------------------------
# STATUS DO DATA LAKE
# ---------------------------------------------------------

with st.expander("📊 Status da Base de Dados"):

    if os.path.exists("data/obsoletos"):
        st.write("Arquivos em obsoletos:", os.listdir("data/obsoletos"))

    if os.path.exists("data/estoque"):
        st.write("Arquivos em estoque:", os.listdir("data/estoque"))


# ---------------------------------------------------------
# TIPO PROCESSAMENTO
# ---------------------------------------------------------

st.subheader("Tipo de processamento")

tipo_processo = st.radio(
    "Escolha o tipo de processamento",
    [
        "Atualizar Evolução de Estoque"
    ]
)

st.markdown("---")


# ---------------------------------------------------------
# DEFINIR PASTA DE DADOS
# ---------------------------------------------------------

if tipo_processo == "Atualizar Obsolescência":
    PASTA_DADOS = "dados_obsoleto"
else:
    PASTA_DADOS = "dados_estoque"


# ---------------------------------------------------------
# LISTAR ARQUIVOS
# ---------------------------------------------------------

if not os.path.exists(PASTA_DADOS):
    st.error(f"A pasta '{PASTA_DADOS}' não existe.")
    st.stop()

zip_files = [f for f in os.listdir(PASTA_DADOS) if f.endswith(".zip")]

if len(zip_files) == 0:
    st.warning("Nenhum arquivo ZIP encontrado.")
    st.stop()


# ---------------------------------------------------------
# REGRA ESTOQUE
# ---------------------------------------------------------

if tipo_processo == "Atualizar Evolução de Estoque" and len(zip_files) > 1:
    st.error("A pasta dados_estoque deve conter apenas um arquivo ZIP.")
    st.stop()


# ---------------------------------------------------------
# SELEÇÃO
# ---------------------------------------------------------

arquivo_selecionado = st.selectbox(
    "Selecione o fechamento para processar",
    zip_files
)


# ---------------------------------------------------------
# PROCESSAMENTO
# ---------------------------------------------------------

if st.button("🚀 Processar Fechamento"):

    caminho_upload = os.path.join(PASTA_DADOS, arquivo_selecionado)

    st.write("Arquivo selecionado:", arquivo_selecionado)

    df_log = carregar_log()

    # -----------------------------------------------------
    # VERIFICAÇÃO DE BLOQUEIO INTELIGENTE
    # -----------------------------------------------------

    bloquear = False

    if arquivo_selecionado in df_log["Arquivo"].values:

        if tipo_processo == "Atualizar Evolução de Estoque":

            if os.path.exists("data/estoque/estoque_historico.parquet"):
                bloquear = True

        else:

            bloquear = True

    if bloquear:

        st.error("⚠ Este arquivo já foi processado anteriormente.")
        st.stop()


    with st.spinner("Processando arquivo..."):

        try:

            if tipo_processo == "Atualizar Obsolescência":

                df_final, df_export = executar_motor(caminho_upload)

                caminho = salvar_fechamento_obsoletos(df_final)

                tipo = "Obsolescência"

            else:

                df_final, df_export = executar_motor_estoque(caminho_upload)

                caminho = salvar_fechamento_estoque(df_final)

                tipo = "Evolução Estoque"

            qtd_registros = len(df_final)

            salvar_log(arquivo_selecionado, qtd_registros, tipo)

            st.success("✅ Processamento concluído!")

            st.write("Arquivo salvo em:", caminho)

            st.write("Registros:", qtd_registros)

            st.download_button(
                label="📥 Baixar Excel Final",
                data=df_export,
                file_name=f"{arquivo_selecionado.replace('.zip','')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.cache_data.clear()

            st.rerun()

        except Exception as e:

            st.error("Erro inesperado durante o processamento.")
            st.exception(e)