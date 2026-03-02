import pandas as pd
import zipfile
import os
import shutil
from pathlib import Path
import io


import uuid

def executar_motor(uploaded_file):

    pasta_base = f"temp_upload_{uuid.uuid4().hex}"

    os.makedirs(pasta_base)
    
    # Extrai o ZIP
    with zipfile.ZipFile(uploaded_file, 'r') as z:
        z.extractall(pasta_base)

    # Lista estrutura encontrada
    pastas_encontradas = os.listdir(pasta_base)

    pastas_esperadas = [
        "01_Entradas_Saidas",
        "02_Estoque_Atual",
        "04_Movimento",
        "05_Empresas",
        "06_Usadas"
    ]

    faltando = [p for p in pastas_esperadas if p not in pastas_encontradas]

    if faltando:
        raise Exception(f"Pastas faltando no ZIP: {faltando}")

    # Se chegou até aqui, estrutura está OK
    df_teste = pd.DataFrame({
        "Status": ["Estrutura validada com sucesso"]
    })

    # Criar Excel em memória corretamente
    buffer = io.BytesIO()
    df_teste.to_excel(buffer, index=False)
    buffer.seek(0)

        # ===============================
    # LEITURA DO ESTOQUE ATUAL
    # ===============================

    pasta_estoque = os.path.join(pasta_base, "02_Estoque_Atual")

    arquivos_excel = [
        f for f in os.listdir(pasta_estoque)
        if f.endswith(".xlsx")
    ]

    if not arquivos_excel:
        raise Exception("Nenhum arquivo .xlsx encontrado em 02_Estoque_Atual")

    caminho_arquivo = os.path.join(pasta_estoque, arquivos_excel[0])

    df_estoque = pd.read_excel(
        caminho_arquivo,
        sheet_name="Detalhado",
        dtype={"Código": str}
    )

    df_estoque = df_estoque.rename(columns={
        "Valor Total": "Custo Total",
        "Código": "Produto",
        "Descrição": "Descricao",
        "Quantidade": "Saldo Atual"
    })

    df_estoque["Produto"] = df_estoque["Produto"].astype(str).str.strip().str.upper()
    df_estoque["Filial"] = df_estoque["Filial"].astype(str).str.title()
    df_estoque["Empresa / Filial"] = df_estoque["Empresa"] + " / " + df_estoque["Filial"]
    df_estoque["ID_UNICO"] = df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]

    # Data base
    DataBase = pd.to_datetime(df_estoque["Data Fechamento"], dayfirst=True).max()

    # Retorno provisório para teste
    df_teste = df_estoque[[
        "Empresa / Filial",
        "Produto",
        "Saldo Atual",
        "Custo Total"
    ]].head(20)

    buffer = io.BytesIO()
    df_teste.to_excel(buffer, index=False)
    buffer.seek(0)

        # ===============================
    # LEITURA DA MATRIZ DE EMPRESAS
    # ===============================

    pasta_empresas = os.path.join(pasta_base, "05_Empresas")
    caminho_matriz = os.path.join(pasta_empresas, "05_Empresas.xlsx")

    if not os.path.exists(caminho_matriz):
        raise Exception("Arquivo 05_Empresas.xlsx não encontrado")

    df_matriz = pd.read_excel(caminho_matriz, dtype=str)
    df_matriz.columns = df_matriz.columns.str.strip()

    if "Mesclado" not in df_matriz.columns or "Empresa / Filial" not in df_matriz.columns:
        raise Exception("Colunas esperadas não encontradas na matriz de empresas")

    return df_teste, buffer.getvalue()
