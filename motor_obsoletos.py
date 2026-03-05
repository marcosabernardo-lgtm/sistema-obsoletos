import pandas as pd
import zipfile
import io
import numpy as np


# ==========================================================
# ESTOQUE
# ==========================================================

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


def executar_estoque(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        arquivo_estoque = next(
            (n for n in z.namelist()
             if "02_Estoque_Atual" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_estoque:
            raise Exception("Arquivo 02_Estoque_Atual não encontrado no ZIP")

        with z.open(arquivo_estoque) as f:
            df = pd.read_excel(
                f,
                sheet_name="Detalhado",
                dtype={"Código": str},
                engine="openpyxl"
            )

        # ==========================================================
        # MAQUINAS USADAS
        # ==========================================================

        arquivos_usadas = [
            n for n in z.namelist()
            if "06_Usadas/" in n and n.lower().endswith(".xlsx")
        ]

        usadas_por_empresa = {}

        for nome in arquivos_usadas:

            nome_upper = nome.upper()

            if "TOOLS" in nome_upper:
                empresa = "Tools"
            elif "MAQUINAS" in nome_upper:
                empresa = "Maquinas"
            elif "ROBOTICA" in nome_upper:
                empresa = "Robotica"
            elif "SERVICE" in nome_upper:
                empresa = "Service"
            else:
                continue

            with z.open(nome) as f:
                df_u = pd.read_excel(f, dtype=str, engine="openpyxl")

            df_u.columns = df_u.columns.str.strip()

            codigos = set(
                df_u["Codigo"]
                .astype(str)
                .str.strip()
                .str.replace(".0", "", regex=False)
            )

            usadas_por_empresa[empresa] = codigos

    df = df.rename(columns={
        "Valor Total": "Custo Total",
        "Código": "Produto",
        "Descrição": "Descricao",
        "Quantidade": "Saldo Atual"
    })

    df["Empresa"] = df["Empresa"].apply(normalizar_empresa)
    df["Filial"] = df["Filial"].astype(str).str.title()

    df["Empresa / Filial"] = df["Empresa"] + " / " + df["Filial"]

    df["Produto"] = (
        df["Produto"]
        .astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
    )

    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]

    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce")
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce")

    if usadas_por_empresa:

        for empresa, codigos in usadas_por_empresa.items():

            mask = (
                df["Empresa / Filial"].str.startswith(empresa)
                & df["Produto"].isin(codigos)
            )

            df.loc[mask, "Conta"] = "Maquina Usada"

    df = df.drop(columns=["Empresa", "Filial"])

    colunas = df.columns.tolist()

    nova_ordem = ["Data Fechamento", "Empresa / Filial"]

    demais = [c for c in colunas if c not in nova_ordem]

    return df[nova_ordem + demais]


# ==========================================================
# MOVIMENTAÇÕES
# ==========================================================

def executar_movimentacoes(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        arquivo_empresas = next(
            (n for n in z.namelist()
             if "05_Empresas" in n and n.endswith(".xlsx")),
            None
        )

        with z.open(arquivo_empresas) as f:
            df_empresas = pd.read_excel(f, dtype=str, engine="openpyxl")

        df_empresas["Mesclado"] = df_empresas["Mesclado"].str.strip()
        df_empresas["Empresa / Filial"] = df_empresas["Empresa / Filial"].str.strip()

        arquivos = [
            f for f in z.namelist()
            if "04_Movimento/" in f and f.lower().endswith(".xlsx")
        ]

        lista = []

        for nome in arquivos:

            with z.open(nome) as arq:
                arquivo_bytes = io.BytesIO(arq.read())

            df = pd.read_excel(arquivo_bytes, dtype=str, engine="openpyxl")

            nome_upper = nome.upper()

            if "ROBOTICA" in nome_upper:
                empresa = "Robotica"
            elif "SERVICE" in nome_upper:
                empresa = "Service"
            else:
                continue

            df["Produto"] = df["Produto"].astype(str).str.strip()
            df["Filial"] = df["Filial"].astype(str).str.strip()

            df["Mesclado"] = empresa + " " + df["Filial"]

            df = df.merge(
                df_empresas[["Mesclado", "Empresa / Filial"]],
                on="Mesclado",
                how="left"
            )

            df["DT Emissao"] = pd.to_datetime(
                df["DT Emissao"],
                errors="coerce",
                dayfirst=True
            )

            df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]

            lista.append(df[["ID_UNICO", "DT Emissao"]])

        df_mov = pd.concat(lista, ignore_index=True)
        df_mov = df_mov[df_mov["DT Emissao"].notna()]

        return (
            df_mov
            .groupby("ID_UNICO", as_index=False)["DT Emissao"]
            .max()
            .rename(columns={"DT Emissao": "Ult_Mov"})
        )


# ==========================================================
# MOTOR FINAL
# ==========================================================

def executar_motor(uploaded_file):

    df_estoque = executar_estoque(uploaded_file)
    df_mov = executar_movimentacoes(uploaded_file)

    df_final = df_estoque.merge(df_mov, on="ID_UNICO", how="left")

    # ------------------------------------------------------
    # PADRONIZAÇÕES
    # ------------------------------------------------------

    df_final["Tipo de Estoque"] = df_final["Tipo de Estoque"].str.title()
    df_final["Conta"] = df_final["Conta"].str.title()

    # PADRONIZA CONTA
    df_final["Conta"] = df_final["Conta"].replace({
        "Material Revenda": "Material De Revenda"
    })

    df_final = df_final.drop(columns=["ID_UNICO"])

    DataBase = pd.to_datetime(df_final["Data Fechamento"].iloc[0])

    df_final["Dias Sem Mov"] = (
        DataBase - df_final["Ult_Mov"]
    ).dt.days.fillna(9999)

    df_final["Meses Ult Mov"] = np.where(
        df_final["Ult_Mov"].notna(),
        (DataBase.year - df_final["Ult_Mov"].dt.year) * 12 +
        (DataBase.month - df_final["Ult_Mov"].dt.month),
        np.nan
    )

    df_final["Status Estoque"] = np.where(
        df_final["Tipo de Estoque"] == "Em Fabricacao",
        "Até 6 meses",
        np.where(df_final["Meses Ult Mov"] > 6, "Obsoleto", "Até 6 meses")
    )

    buffer = io.BytesIO()

    df_final.to_excel(buffer, index=False)

    buffer.seek(0)

    return df_final, buffer.getvalue()
