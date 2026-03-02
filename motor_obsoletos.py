import pandas as pd
import zipfile
import io
import os
from datetime import datetime


def executar_motor(uploaded_file):

    # ===============================
    # EXTRAIR ZIP
    # ===============================
    with zipfile.ZipFile(uploaded_file) as z:
        z.extractall("temp")

    # ===============================
    # LOCALIZAR ARQUIVO ESTOQUE
    # ===============================
    caminho_estoque = None

    for root, dirs, files in os.walk("temp"):
        for file in files:
            if "Estoque" in file and file.endswith(".xlsx"):
                caminho_estoque = os.path.join(root, file)

    if caminho_estoque is None:
        raise Exception("Arquivo de estoque não encontrado no ZIP")

    # ===============================
    # LEITURA CORRETA DA ABA DETALHADO
    # ===============================
    df_estoque = pd.read_excel(
        caminho_estoque,
        sheet_name="Detalhado",
        dtype={"Código": str}
    )

    # ===============================
    # RENOMEAR COLUNAS
    # ===============================
    df_estoque = df_estoque.rename(columns={
        "Valor Total": "Custo Total",
        "Código": "Produto",
        "Descrição": "Descricao",
        "Quantidade": "Saldo Atual"
    })

    # ===============================
    # GARANTIR QUE COLUNAS EXISTEM
    # ===============================
    colunas_necessarias = [
        "Data Fechamento",
        "Empresa",
        "Filial",
        "Produto",
        "Saldo Atual",
        "Custo Total"
    ]

    for col in colunas_necessarias:
        if col not in df_estoque.columns:
            raise Exception(f"Coluna {col} não encontrada no estoque")

    # ===============================
    # NORMALIZA EMPRESA (IGUAL PYTHON ORIGINAL)
    # ===============================
    def normalizar_empresa(nome):
        nome = str(nome).upper()
        if "TOOLS" in nome:
            return "Tools"
        if "MAQUINAS" in nome:
            return "Maquinas"
        if "ALLSERVICE" in nome:
            return "Service"
        if "ROBOTICA" in nome:
            return "Robotica"
        return nome

    df_estoque["Empresa"] = df_estoque["Empresa"].apply(normalizar_empresa)
    df_estoque["Filial"] = df_estoque["Filial"].astype(str).str.title()

    df_estoque["Empresa / Filial"] = (
        df_estoque["Empresa"] + " / " + df_estoque["Filial"]
    )

    # ===============================
    # GARANTIR ZERO À ESQUERDA
    # ===============================
    df_estoque["Produto"] = (
        df_estoque["Produto"]
        .astype(str)
        .str.strip()
        .str.zfill(6)
    )

    # ===============================
    # CONVERTER NUMÉRICOS CORRETAMENTE
    # ===============================
    df_estoque["Saldo Atual"] = pd.to_numeric(
        df_estoque["Saldo Atual"], errors="coerce"
    )

    df_estoque["Custo Total"] = pd.to_numeric(
        df_estoque["Custo Total"], errors="coerce"
    )

    # ===============================
    # DATA BASE
    # ===============================
    df_estoque["Data Fechamento"] = pd.to_datetime(
        df_estoque["Data Fechamento"],
        dayfirst=True,
        errors="coerce"
    )

    DataBase = df_estoque["Data Fechamento"].max()

    df_estoque["Data_Base"] = DataBase

    # ===============================
    # ID UNICO
    # ===============================
    df_estoque["ID_UNICO"] = (
        df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]
    )

    # ===============================
    # ESTRUTURA FINAL PADRÃO
    # ===============================
    df_final = df_estoque[[
        "Data_Base",
        "Empresa / Filial",
        "Produto",
        "Saldo Atual",
        "Custo Total",
        "ID_UNICO"
    ]].copy()

    # ===============================
    # EXPORTAR PARA EXCEL
    # ===============================
    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
