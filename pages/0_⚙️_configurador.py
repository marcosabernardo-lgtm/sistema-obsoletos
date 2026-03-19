import streamlit as st
import pandas as pd
import os
from datetime import datetime

from motor.motor_obsoletos import executar_motor
from motor.motor_estoque import executar_motor_estoque
from motor.motor_dio import executar_motor_dio
from motor.motor_inventario import executar_motor_inventario

from storage.base_obsoletos_lake import salvar_fechamento_obsoletos
from storage.base_estoque_lake import salvar_fechamento_estoque
from storage.base_inventario_lake import salvar_fechamento_inventario

st.set_page_config(page_title="Configurador", layout="wide")

# -------------------------------------------------
# CSS
# -------------------------------------------------

st.markdown("""
<style>

section[data-testid="stSidebar"]{ width:260px !important; }

section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {
    border: 2px solid #EC6E21 !important;
    border-radius: 8px !important;
    background-color: #005562 !important;
    color: white !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] span,
section[data-testid="stSidebar"] div[data-baseweb="select"] div {
    color: white !important;
}

section[data-testid="stSidebar"] label {
    color: white !important;
    font-weight: 600 !important;
}

.kpi-card{
    background-color:#005562;
    border:2px solid #EC6E21;
    padding:16px;
    border-radius:10px;
    text-align:center;
}

.kpi-title{ font-size:13px; color:white; }
.kpi-value{ font-size:22px; font-weight:700; color:white; }

</style>
""", unsafe_allow_html=True)

st.title("⚙️ Configurador")
st.markdown("Processamento de fechamentos mensais e administração do sistema.")
st.markdown("---")

# -------------------------------------------------
# ESTRUTURA DE PASTAS
# -------------------------------------------------

os.makedirs("data", exist_ok=True)
os.makedirs("data/obsoletos", exist_ok=True)
os.makedirs("data/estoque", exist_ok=True)
os.makedirs("data/dio", exist_ok=True)
os.makedirs("data/inventario", exist_ok=True)

LOG_PATH = "data/log_uploads.parquet"

# -------------------------------------------------
# FUNÇÕES DE LOG
# -------------------------------------------------

def carregar_log():
    if os.path.exists(LOG_PATH):
        return pd.read_parquet(LOG_PATH)
    return pd.DataFrame(columns=["Arquivo", "Data", "Registros", "Tipo"])


def salvar_log(nome_zip, registros, tipo):
    df_log = carregar_log()
    from datetime import timezone, timedelta
    agora = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))
    novo = pd.DataFrame([{"Arquivo": nome_zip, "Data": agora, "Registros": registros, "Tipo": tipo}])
    df_log = pd.concat([df_log, novo], ignore_index=True)
    df_log.to_parquet(LOG_PATH, index=False)
    return df_log

# -------------------------------------------------
# ZONA DE PERIGO
# -------------------------------------------------

with st.expander("⚠️ Zona de Perigo — Resetar Base"):

    col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns(5)

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
        if st.button("🗑 Resetar DIO"):
            import shutil
            if os.path.exists("data/dio"):
                shutil.rmtree("data/dio")
                os.makedirs("data/dio", exist_ok=True)
            if os.path.exists(LOG_PATH):
                df_log = carregar_log()
                df_log = df_log[df_log["Tipo"] != "DIO"]
                df_log.to_parquet(LOG_PATH, index=False)
            st.success("Base de DIO resetada.")
            st.cache_data.clear()
            st.rerun()

    with col_r4:
        if st.button("🗑 Resetar Inventário"):
            import shutil
            if os.path.exists("data/inventario"):
                shutil.rmtree("data/inventario")
                os.makedirs("data/inventario", exist_ok=True)
            if os.path.exists(LOG_PATH):
                df_log = carregar_log()
                df_log = df_log[df_log["Tipo"] != "Inventário"]
                df_log.to_parquet(LOG_PATH, index=False)
            st.success("Base de inventário resetada.")
            st.cache_data.clear()
            st.rerun()

    with col_r5:
        if st.button("🗑 Resetar Tudo"):
            import shutil
            if os.path.exists("data"):
                shutil.rmtree("data")
            st.success("Todas as bases removidas.")
            st.cache_data.clear()
            st.rerun()

st.markdown("---")

# -------------------------------------------------
# STATUS DA BASE
# -------------------------------------------------

with st.expander("📊 Status da Base de Dados"):
    if os.path.exists("data/obsoletos"):
        st.write("Obsoletos:", os.listdir("data/obsoletos"))
    if os.path.exists("data/estoque"):
        st.write("Estoque:", os.listdir("data/estoque"))
    if os.path.exists("data/dio"):
        st.write("DIO:", os.listdir("data/dio"))
    if os.path.exists("data/inventario"):
        st.write("Inventário:", os.listdir("data/inventario"))

st.markdown("---")

# -------------------------------------------------
# TIPO DE PROCESSAMENTO
# -------------------------------------------------

st.subheader("Tipo de processamento")

tipo_processo = st.radio(
    "Escolha o tipo de processamento",
    [
        "Atualizar Evolução de Estoque",
        "Atualizar Obsolescência",
        "Atualizar DIO",
        "Atualizar Inventário",
    ]
)

st.markdown("---")


# -------------------------------------------------
# FLUXO: OBSOLESCÊNCIA (lote automático)
# -------------------------------------------------

if tipo_processo == "Atualizar Obsolescência":

    PASTA_OBS = "dados_obsoleto"

    if not os.path.exists(PASTA_OBS):
        st.error(f"A pasta '{PASTA_OBS}' não existe.")
        st.stop()

    zip_files_obs = sorted([f for f in os.listdir(PASTA_OBS) if f.endswith(".zip")])

    if not zip_files_obs:
        st.warning("Nenhum arquivo ZIP encontrado em 'dados_obsoleto'.")
        st.stop()

    df_log = carregar_log()
    ja_processados = set(df_log[df_log["Tipo"] == "Obsolescência"]["Arquivo"].values)
    novos = [f for f in zip_files_obs if f not in ja_processados]

    st.markdown("**Arquivos em `dados_obsoleto/`:**")
    for arq in zip_files_obs:
        if arq in ja_processados:
            st.markdown(f"✅ `{arq}` — já processado")
        else:
            st.markdown(f"🟡 `{arq}` — **pendente**")

    st.markdown("")

    if not novos:
        st.success("Todos os arquivos já foram processados.")
        st.stop()

    st.info(f"**{len(novos)} arquivo(s) novo(s)** serão processados: {', '.join(novos)}")

    if st.button("🚀 Processar Fechamentos"):
        total_registros = 0
        erros = []

        for arquivo in novos:
            caminho = os.path.join(PASTA_OBS, arquivo)
            st.write(f"⏳ Processando `{arquivo}`...")
            try:
                with st.spinner(f"Processando {arquivo}..."):
                    df_final, _ = executar_motor(caminho)
                    salvar_fechamento_obsoletos(df_final)
                    qtd = len(df_final)
                    total_registros += qtd
                    salvar_log(arquivo, qtd, "Obsolescência")
                    st.write(f"✅ `{arquivo}` — {qtd} registros")
            except Exception as e:
                erros.append(arquivo)
                st.error(f"❌ Erro em `{arquivo}`: {e}")

        if erros:
            st.warning(f"Concluído com erros em: {', '.join(erros)}")
        else:
            st.success(f"✅ Todos os fechamentos processados! Total: {total_registros} registros")

        st.cache_data.clear()
        st.rerun()

    st.stop()


# -------------------------------------------------
# FLUXO: INVENTÁRIO
# -------------------------------------------------

if tipo_processo == "Atualizar Inventário":

    PASTA_INV = "analytics/dados_inventario"

    if not os.path.exists(PASTA_INV):
        st.error(f"A pasta '{PASTA_INV}' não existe.")
        st.stop()

    zip_files_inv = sorted([f for f in os.listdir(PASTA_INV) if f.endswith(".zip")])

    if not zip_files_inv:
        st.warning("Nenhum arquivo ZIP encontrado em 'analytics/dados_inventario'.")
        st.stop()

    df_log = carregar_log()
    ja_proc_inv = set(df_log[df_log["Tipo"] == "Inventário"]["Arquivo"].values)
    novos_inv = [f for f in zip_files_inv if f not in ja_proc_inv]

    st.markdown("**Arquivos em `analytics/dados_inventario/`:**")
    for arq in zip_files_inv:
        if arq in ja_proc_inv:
            st.markdown(f"✅ `{arq}` — já processado")
        else:
            st.markdown(f"🟡 `{arq}` — **pendente**")

    st.markdown("")

    if not novos_inv:
        st.success("Todos os arquivos já foram processados.")
        st.stop()

    st.info(f"**{len(novos_inv)} arquivo(s)** serão processados: {', '.join(novos_inv)}")

    if st.button("🚀 Processar Inventário"):
        total_registros = 0
        erros = []

        for arquivo in novos_inv:
            caminho = os.path.join(PASTA_INV, arquivo)
            st.write(f"⏳ Processando `{arquivo}`...")
            try:
                with st.spinner(f"Processando {arquivo}..."):
                    df_final, _ = executar_motor_inventario(caminho)
                    salvar_fechamento_inventario(df_final)
                    qtd = len(df_final)
                    total_registros += qtd
                    salvar_log(arquivo, qtd, "Inventário")
                    st.write(f"✅ `{arquivo}` — {qtd} registros")
            except Exception as e:
                erros.append(arquivo)
                st.error(f"❌ Erro em `{arquivo}`: {e}")

        if erros:
            st.warning(f"Concluído com erros em: {', '.join(erros)}")
        else:
            st.success(f"✅ Inventário processado! Total: {total_registros} registros")

        st.cache_data.clear()
        st.rerun()

    st.stop()


# -------------------------------------------------
# FLUXO: ESTOQUE E DIO
# -------------------------------------------------

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

if tipo_processo == "Atualizar DIO":
    if not os.path.exists(PASTA_OBSOLETOS):
        st.error("A pasta 'dados_obsoleto' não existe. O DIO precisa dos ZIPs de obsoletos.")
        st.stop()
    zips_obsoletos = [f for f in os.listdir(PASTA_OBSOLETOS) if f.endswith(".zip")]
    if not zips_obsoletos:
        st.error("Nenhum ZIP encontrado em 'dados_obsoleto'.")
        st.stop()
    st.info(f"📂 Serão usados **{len(zips_obsoletos)} ZIP(s)** de obsoletos: " + ", ".join(zips_obsoletos))

if len(zip_files) > 1:
    st.error("A pasta dados_estoque deve conter apenas um arquivo ZIP.")
    st.stop()

arquivo_selecionado = st.selectbox("Selecione o fechamento para processar", zip_files)

if st.button("🚀 Processar Fechamento"):

    caminho_upload = os.path.join(PASTA_DADOS, arquivo_selecionado)
    df_log = carregar_log()

    bloquear = False
    if arquivo_selecionado in df_log["Arquivo"].values:
        if tipo_processo == "Atualizar Evolução de Estoque":
            if os.path.exists("data/estoque/estoque_historico.parquet"):
                bloquear = True
        elif tipo_processo == "Atualizar DIO":
            data_str = arquivo_selecionado.replace(".zip", "")
            if os.path.exists(f"data/dio/{data_str}.parquet"):
                bloquear = True

    if bloquear:
        st.error("⚠ Este arquivo já foi processado anteriormente.")
        st.stop()

    with st.spinner("Processando arquivo..."):
        try:
            if tipo_processo == "Atualizar DIO":
                df_final, df_export = executar_motor_dio(
                    caminho_zip_estoque=caminho_upload,
                    pasta_zips_obsoletos=PASTA_OBSOLETOS
                )
                caminho = f"data/dio/{arquivo_selecionado.replace('.zip', '')}.parquet"
                tipo = "DIO"
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
                file_name=f"{arquivo_selecionado.replace('.zip','')}_{'dio' if tipo == 'DIO' else 'estoque'}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.cache_data.clear()
            st.rerun()

        except Exception as e:
            st.error("Erro inesperado durante o processamento.")
            st.exception(e)
