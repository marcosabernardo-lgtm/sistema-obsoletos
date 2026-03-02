import os
import zipfile
import io
import pandas as pd
from datetime import datetime


def executar_motor(uploaded_file):

    # =====================================================
    # EXTRAÇÃO DO ZIP
    # =====================================================

    pasta_base = "dados_temp"

    if os.path.exists(pasta_base):
        import shutil
        shutil.rmtree(pasta_base)

    os.makedirs(pasta_base)

    with zipfile.ZipFile(uploaded_file, 'r') as z:
        z.extractall(pasta_base)

    # =====================================================
    # LEITURA DO ESTOQUE
    # =====================================================

    pasta_estoque = os.path.join(pasta_base, "02_Estoque_Atual")

    arquivos = [
        f for f in os.listdir(pasta_estoque)
        if f.endswith(".xlsx")
    ]

    if not arquivos:
        raise Exception("Nenhum arquivo de estoque encontrado")

    caminho_estoque = os.path.join(pasta_estoque, arquivos[0])

    df_estoque = pd.read_excel(caminho_estoque)

    df_estoque.columns = df_estoque.columns.str.strip()

    colunas_necessarias = [
        "Empresa / Filial",
        "Produto",
        "Saldo Atual",
        "Custo Total"
    ]

    for col in colunas_necessarias:
        if col not in df_estoque.columns:
            raise Exception(f"Coluna obrigatória não encontrada: {col}")

    df_final = df_estoque[colunas_necessarias].copy()

    # =====================================================
    # DATA BASE
    # =====================================================

    if "Data Fechamento" in df_estoque.columns:
        data_base = df_estoque["Data Fechamento"].max()
    else:
        data_base = datetime.today()

    df_final["Data_Base"] = data_base

    # =====================================================
    # HISTÓRICO AUTOMÁTICO
    # =====================================================

    historico_path = "historico_obsoletos.csv"

    df_hist_atual = df_final.copy()
    df_hist_atual["Data_Processamento"] = datetime.now()

    if os.path.exists(historico_path):
        df_hist_antigo = pd.read_csv(historico_path, dtype=str)
        df_hist_novo = pd.concat(
            [df_hist_antigo, df_hist_atual.astype(str)],
            ignore_index=True
        )
    else:
        df_hist_novo = df_hist_atual.astype(str)

    df_hist_novo.to_csv(historico_path, index=False)

    # =====================================================
    # GERAÇÃO DO EXCEL PARA DOWNLOAD
    # =====================================================

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
