import pandas as pd
import numpy as np
import zipfile
import io
import os
from pathlib import Path


def executar_motor(uploaded_file):

    # ============================================================
    # EXTRAÇÃO DO ZIP
    # ============================================================

    zip_bytes = io.BytesIO(uploaded_file.read())

    with zipfile.ZipFile(zip_bytes) as z:
        z.extractall("temp_projeto")

    pasta_base = "temp_projeto"

    # ============================================================
    # 1️⃣ ESTOQUE ATUAL
    # ============================================================

    pasta_estoque = os.path.join(pasta_base, "02_Estoque_Atual")

    arquivos_estoque = list(Path(pasta_estoque).glob("*.xlsx"))
    if not arquivos_estoque:
        raise Exception("Arquivo de estoque não encontrado em 02_Estoque_Atual")

    caminho_estoque = str(arquivos_estoque[0])

    df_estoque = pd.read_excel(
        caminho_estoque,
        sheet_name="Detalhado",
        dtype={"Código": str}
    )

    df_estoque = df_estoque.rename(columns={
        "Valor Total": "Custo Total",
        "Código": "Produto",
        "Descrição": "Descricao",
        "Quantidade": "Saldo Atual"
    })

    def normalizar_empresa(nome):
        nome = str(nome).upper()
        if "TOOLS" in nome: return "Tools"
        if "MAQUINAS" in nome: return "Maquinas"
        if "ALLSERVICE" in nome: return "Service"
        if "ROBOTICA" in nome: return "Robotica"
        return nome

    df_estoque["Empresa"] = df_estoque["Empresa"].apply(normalizar_empresa)
    df_estoque["Filial"] = df_estoque["Filial"].astype(str).str.title()

    df_estoque["Empresa / Filial"] = (
        df_estoque["Empresa"] + " / " + df_estoque["Filial"]
    )

    df_estoque["Produto"] = (
        df_estoque["Produto"]
        .astype(str)
        .str.strip()
        .str.upper()
        .str.zfill(6)
    )

    df_estoque["ID_UNICO"] = (
        df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]
    )

    DataBase = pd.to_datetime(
        df_estoque["Data Fechamento"],
        dayfirst=True
    ).max()

    # ============================================================
    # 2️⃣ MOVIMENTACOES_BASE
    # ============================================================

    pasta_mov = os.path.join(pasta_base, "04_Movimento")
    pasta_emp = os.path.join(pasta_base, "05_Empresas")
    caminho_matriz = os.path.join(pasta_emp, "05_Empresas.xlsx")

    arquivos_csv = list(Path(pasta_mov).glob("*.csv"))
    lista = []

    for arq in arquivos_csv:
        with open(arq, "r", encoding="cp1252") as f:
            linhas = f.readlines()[2:]

        linhas = [l.strip() for l in linhas if l.strip()]
        cab = linhas[0].replace('"','').split(",")
        dados = [l.replace('"','').split(",")[:len(cab)] for l in linhas[1:]]

        df_temp = pd.DataFrame(dados, columns=cab)
        df_temp["Origem"] = arq.name
        lista.append(df_temp)

    df_mov = pd.concat(lista, ignore_index=True)

    df_mov["Quantidade"] = pd.to_numeric(df_mov["Quantidade"], errors="coerce")
    df_mov["DT Emissao"] = pd.to_datetime(df_mov["DT Emissao"], dayfirst=True, errors="coerce")

    df_mov = df_mov[(df_mov["Quantidade"]!=0) & df_mov["DT Emissao"].notna()]

    df_mov["Produto"] = (
        df_mov["Produto"]
        .astype(str)
        .str.strip()
        .str.upper()
        .str.zfill(6)
    )

    df_mov["Empresa"] = df_mov["Origem"].str.replace(".csv","",regex=False).str.split("_").str[1]
    df_mov["Mesclado"] = df_mov["Empresa"] + " " + df_mov["Filial"]

    df_matriz = pd.read_excel(caminho_matriz, dtype=str)

    df_mov = df_mov.merge(
        df_matriz[["Mesclado","Empresa / Filial"]],
        on="Mesclado",
        how="left"
    )

    df_mov["Empresa / Filial"] = df_mov["Empresa / Filial"].fillna("N/D")

    df_mov = df_mov[["Empresa / Filial","Produto","Quantidade","DT Emissao"]]

    df_mov["ID_UNICO"] = (
        df_mov["Empresa / Filial"] + "|" + df_mov["Produto"]
    )

    # ============================================================
    # 3️⃣ CONSOLIDAÇÃO MOVIMENTAÇÕES
    # ============================================================

    df_mov["DtEnt"] = df_mov["DT Emissao"]

    df_cons = df_mov.groupby(
        ["Empresa / Filial","Produto"],
        as_index=False
    ).agg(
        Ult_Mov=("DtEnt","max")
    )

    df_cons["ID_UNICO"] = (
        df_cons["Empresa / Filial"] + "|" + df_cons["Produto"]
    )

    # ============================================================
    # 4️⃣ MERGE FINAL
    # ============================================================

    df_final = df_estoque.merge(
        df_cons[["ID_UNICO","Ult_Mov"]],
        on="ID_UNICO",
        how="left"
    )

    df_final["Dias Sem Mov"] = (
        DataBase - df_final["Ult_Mov"]
    ).dt.days.fillna(9999)

    df_final["Meses Ult Mov"] = np.where(
        df_final["Ult_Mov"].notna(),
        (DataBase.year - df_final["Ult_Mov"].dt.year)*12 +
        (DataBase.month - df_final["Ult_Mov"].dt.month),
        np.nan
    )

    df_final["Status Estoque"] = np.where(
        df_final["Dias Sem Mov"] > 180,
        "Obsoleto",
        "Até 6 meses"
    )

    # ============================================================
    # EXPORTAÇÃO
    # ============================================================

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
