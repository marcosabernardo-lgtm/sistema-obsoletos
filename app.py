import streamlit as st
import pandas as pd
import os
from datetime import datetime

from motor.motor_obsoletos import executar_motor
from motor.motor_estoque import executar_motor_estoque
from motor.motor_dio import executar_motor_dio
from motor.motor_inventario import processar_zip as executar_motor_inventario

from storage.base_obsoletos_lake import salvar_fechamento_obsoletos
from storage.base_estoque_lake import salvar_fechamento_estoque

st.set_page_config(page_title="Processamento de Estoque", layout="wide")

# ---------------------------------------------------------
# GARANTIR ESTRUTURA DE PASTAS
# ---------------------------------------------------------

os.makedirs("data", exist_ok=True)
os.makedirs("data/obsoletos", exist_ok=True)
os.makedirs("data/estoque", exist_ok=True)
os.makedirs("data/dio", exist_ok=True)
os.makedirs("data/inventario", exist_ok=True)

LOG_PATH = "data/log_uploads.parquet"

st.title("📊 Análise Gerencial de Estoques - Grupo Alltech")

st.markdown(
"""
Este painel consolida informações estratégicas de estoque, permitindo análise da evolução, identificação de riscos de obsolescência e suporte à tomada de decisão.

As informações incluem:

• Evolução do valor total em estoque  
• Identificação de itens obsoletos  
• Classificação por tempo sem movimentação  
• Distribuição por empresa e filial  
• DIO — Days Inventory Outstanding por produto
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

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)

    with col_r1:
        if st.button("🗑 Resetar Estoque"):
            import shutil
            if os.path.exists("data/estoque"):
                shutil.rmtree("data/estoque")
                os.makedirs("data/estoque", exist_ok=True)
            st.success("Base de estoque resetada.")
            st.cache_data.clear()
            st.rerun()

    with col_r2:
        if st.button("🗑 Resetar Obsoletos"):
            import shutil
            if os.path.exists("data/obsoletos"):
                shutil.rmtree("data/obsoletos")
                os.makedirs("data/obsoletos", exist_ok=True)
            st.success("Base de obsoletos resetada.")
            st.cache_data.clear()
            st.rerun()

    with col_r3:
        if st.button("🗑 Resetar DIO"):
            import shutil
            if os.path.exists("data/dio"):
                shutil.rmtree("data/dio")
                os.makedirs("data/dio", exist_ok=True)
            st.success("Base de DIO resetada.")
            st.cache_data.clear()
            st.rerun()

    with col_r4:
        if st.button("🗑 Resetar Inventário"):
            import shutil
            if os.path.exists("data/inventario"):
                shutil.rmtree("data/inventario")
                os.makedirs("data/inventario", exist_ok=True)
            st.success("Base de inventário resetada.")
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

    if os.path.exists("data/dio"):
        st.write("Arquivos em DIO:", os.listdir("data/dio"))

    if os.path.exists("data/inventario"):
        st.write("Arquivos em inventário:", os.listdir("data/inventario"))


# ---------------------------------------------------------
# TIPO PROCESSAMENTO
# ---------------------------------------------------------

st.subheader("Tipo de processamento")

tipo_processo = st.radio(
    "Escolha o tipo de processamento",
    [
        "Atualizar Evolução de Estoque",
        "Atualizar Obsolescência",
        "Atualizar DIO",
        "Atualizar Inventário"
    ]
)

st.markdown("---")


# ---------------------------------------------------------
# FLUXO INVENTÁRIO
# ---------------------------------------------------------

if tipo_processo == "Atualizar Inventário":

    PASTA_INV = "analytics/dados_inventario"

    if not os.path.exists(PASTA_INV):
        st.error("Pasta analytics/dados_inventario não encontrada")
        st.stop()

    arquivos = [f for f in os.listdir(PASTA_INV) if f.endswith(".zip")]

    if len(arquivos) == 0:
        st.warning("Nenhum ZIP encontrado em analytics/dados_inventario")
        st.stop()

    if len(arquivos) > 1:
        st.error("A pasta deve conter apenas um ZIP")
        st.stop()

    arquivo = arquivos[0]

    st.info(f"Arquivo encontrado: {arquivo}")

    if st.button("🚀 Processar Inventário"):

        try:

            executar_motor_inventario()

            st.success("Inventário processado com sucesso")

            st.cache_data.clear()
            st.rerun()

        except Exception as e:

            st.error("Erro ao processar inventário")
            st.exception(e)

    st.stop()


# ---------------------------------------------------------
# DEFINIR PASTA DE DADOS
# ---------------------------------------------------------

if tipo_processo == "Atualizar DIO":
    PASTA_DADOS = "dados_estoque"
    PASTA_OBSOLETOS = "dados_obsoleto"
else:
    PASTA_DADOS = "dados_estoque"

if not os.path.exists(PASTA_DADOS):
    st.error(f"A pasta '{PASTA_DADOS}' não existe.")
    st.stop()

zip_files = [f for f in os.listdir(PASTA_DADOS) if f.endswith(".zip")]

if len(zip_files) == 0:
    st.warning("Nenhum arquivo ZIP encontrado.")
    st.stop()

if len(zip_files) > 1:
    st.error("A pasta dados_estoque deve conter apenas um arquivo ZIP.")
    st.stop()

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

    with st.spinner("Processando arquivo..."):

        try:

            if tipo_processo == "Atualizar DIO":

                df_final, df_export = executar_motor_dio(
                    caminho_zip_estoque=caminho_upload,
                    pasta_zips_obsoletos="dados_obsoleto"
                )

                caminho = f"data/dio/{arquivo_selecionado.replace('.zip','')}.parquet"

                os.makedirs("data/dio", exist_ok=True)
                df_final.to_parquet(caminho, index=False)

                tipo = "DIO"

            else:

                df_final, df_export = executar_motor_estoque(caminho_upload)
                caminho = salvar_fechamento_estoque(df_final)
                tipo = "Evolução Estoque"

            qtd_registros = len(df_final)

            salvar_log(arquivo_selecionado, qtd_registros, tipo)

            st.success("Processamento concluído")
            st.write("Arquivo salvo em:", caminho)
            st.write("Registros:", qtd_registros)

            st.cache_data.clear()
            st.rerun()

        except Exception as e:

            st.error("Erro inesperado durante o processamento.")
            st.exception(e)