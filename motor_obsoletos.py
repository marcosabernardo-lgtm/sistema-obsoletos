import pandas as pd
import zipfile
import io
import os
import shutil
from datetime import datetime

def executar_motor(uploaded_file):

    # ===============================
    # EXTRAÇÃO DO ZIP
    # ===============================

    pasta_base = "temp_upload"

    if os.path.exists(pasta_base):
        shutil.rmtree(pasta_base)

    os.makedirs(pasta_base)

    with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
        zip_ref.extractall(pasta_base)

    # ===============================
    # LEITURA DO ESTOQUE ATUAL
    # ===============================

    pasta_estoque = os.path.join(pasta_base, "02_Estoque_Atual")

    arquivos = [f for f in os.listdir(pasta_estoque) if f.endswith(".xlsx")]

    if not arquivos:
        raise Exception("Nenhum arquivo Excel encontrado em 02_Estoque_Atual")

    caminho_estoque = os.path.join(pasta_estoque, arquivos[0])

    df_estoque = pd.read_excel(caminho_estoque)

    colunas_necessarias = [
        "Empresa / Filial",
        "Produto",
        "Saldo Atual",
        "Custo Total"
    ]

    for col in colunas_necessarias:
        if col not in df_estoque.columns:
            raise Exception(f"Coluna {col} não encontrada no estoque")

    df_final = df_estoque[colunas_necessarias].copy()

    # ===============================
    # HISTÓRICO AUTOMÁTICO
    # ===============================

    historico_path = "historico_obsoletos.csv"

    df_final["Data_Base"] = datetime.today().date()

    if os.path.exists(historico_path):
        df_hist_antigo = pd.read_csv(historico_path, dtype=str)
        df_historico = pd.concat(
            [df_hist_antigo, df_final.astype(str)],
            ignore_index=True
        )
    else:
        df_historico = df_final.astype(str)

    df_historico.to_csv(historico_path, index=False)

    # ===============================
    # EXPORTAÇÃO PARA EXCEL
    # ===============================

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
