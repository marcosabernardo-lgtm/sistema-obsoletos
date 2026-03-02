import os
import zipfile
import tempfile
import pandas as pd
import io
from datetime import datetime


def executar_motor(uploaded_file):

    # ==============================
    # CRIAR PASTA TEMPORÁRIA
    # ==============================
    temp_dir = tempfile.mkdtemp()

    zip_path = os.path.join(temp_dir, "upload.zip")

    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # ==============================
    # LOCALIZAR ARQUIVO DE ESTOQUE
    # ==============================
    pasta_estoque = os.path.join(temp_dir, "02_Estoque_Atual")

    arquivos_excel = [
        f for f in os.listdir(pasta_estoque)
        if f.endswith(".xlsx")
    ]

    if not arquivos_excel:
        raise Exception("Nenhum arquivo Excel encontrado em 02_Estoque_Atual")

    caminho_estoque = os.path.join(pasta_estoque, arquivos_excel[0])

    # ==============================
    # LER ABA CORRETA: DETALHADO
    # ==============================
    df_estoque = pd.read_excel(
        caminho_estoque,
        sheet_name="Detalhado",
        dtype=str  # 🔥 ESSENCIAL para manter zero à esquerda
    )

    df_estoque.columns = df_estoque.columns.str.strip()

    # ==============================
    # VALIDAR COLUNAS NECESSÁRIAS
    # ==============================
    colunas_necessarias = [
        "Data Fechamento",
        "Empresa",
        "Filial",
        "Tipo de Estoque",
        "Conta",
        "Código",
        "Descrição",
        "Unid",
        "Quantidade",
        "Vlr Unit",
        "Valor Total"
    ]

    for col in colunas_necessarias:
        if col not in df_estoque.columns:
            raise Exception(f"Coluna {col} não encontrada no estoque")

    # ==============================
    # AJUSTES DE TIPO NUMÉRICO
    # (SEM mexer no Código!)
    # ==============================

    df_estoque["Quantidade"] = (
        df_estoque["Quantidade"]
        .str.replace(",", ".", regex=False)
    )

    df_estoque["Vlr Unit"] = (
        df_estoque["Vlr Unit"]
        .str.replace(",", ".", regex=False)
    )

    df_estoque["Valor Total"] = (
        df_estoque["Valor Total"]
        .str.replace(",", ".", regex=False)
    )

    df_estoque["Quantidade"] = pd.to_numeric(df_estoque["Quantidade"], errors="coerce")
    df_estoque["Vlr Unit"] = pd.to_numeric(df_estoque["Vlr Unit"], errors="coerce")
    df_estoque["Valor Total"] = pd.to_numeric(df_estoque["Valor Total"], errors="coerce")

    # ==============================
    # CRIAR ESTRUTURA FINAL PADRÃO
    # ==============================

    df_final = pd.DataFrame()

    df_final["Data Fechamento"] = df_estoque["Data Fechamento"]
    df_final["Empresa"] = df_estoque["Empresa"]
    df_final["Filial"] = df_estoque["Filial"]
    df_final["Tipo de Estoque"] = df_estoque["Tipo de Estoque"]
    df_final["Conta"] = df_estoque["Conta"]

    # 🔥 MANTÉM ZERO À ESQUERDA
    df_final["Produto"] = df_estoque["Código"]

    df_final["Descrição"] = df_estoque["Descrição"]
    df_final["Unid"] = df_estoque["Unid"]
    df_final["Saldo Atual"] = df_estoque["Quantidade"]
    df_final["Vlr Unit"] = df_estoque["Vlr Unit"]
    df_final["Custo Total"] = df_estoque["Valor Total"]

    # Empresa / Filial
    df_final["Empresa / Filial"] = (
        df_final["Empresa"] + " / " + df_final["Filial"]
    )

    # ID_UNICO
    df_final["ID_UNICO"] = (
        df_final["Empresa / Filial"] + "|" + df_final["Produto"]
    )

    # ==============================
    # EXPORTAÇÃO PARA EXCEL
    # ==============================
    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
