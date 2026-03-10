import pandas as pd
import zipfile
import io


# ==========================================================
# NORMALIZA EMPRESA
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


# ==========================================================
# MOTOR EVOLUÇÃO ESTOQUE
# ==========================================================

def executar_motor_estoque(caminho_zip):

    with zipfile.ZipFile(caminho_zip, "r") as z:

        # ------------------------------------------------------
        # ESTOQUE ATUAL
        # ------------------------------------------------------

        arquivo_estoque = next(
            (
                n for n in z.namelist()
                if "02_Estoque_Atual" in n and n.endswith(".xlsx")
            ),
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

        # ------------------------------------------------------
        # MAQUINAS USADAS
        # ------------------------------------------------------

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

                df_u = pd.read_excel(
                    f,
                    dtype=str,
                    engine="openpyxl"
                )

            df_u.columns = df_u.columns.str.strip()

            codigos = set(
                df_u["Codigo"]
                .astype(str)
                .str.strip()
                .str.replace(".0", "", regex=False)
            )

            usadas_por_empresa[empresa] = codigos

    # ------------------------------------------------------
    # TRATAMENTO BASE
    # ------------------------------------------------------

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

    df["Saldo Atual"] = pd.to_numeric(
        df["Saldo Atual"],
        errors="coerce"
    )

    df["Custo Total"] = pd.to_numeric(
        df["Custo Total"],
        errors="coerce"
    )

    # ------------------------------------------------------
    # DATA FECHAMENTO
    # ------------------------------------------------------

    df["Data Fechamento"] = pd.to_datetime(
    df["Data Fechamento"],
    errors="coerce"
    )

    # ------------------------------------------------------
    # MARCAR MAQUINA USADA
    # ------------------------------------------------------

    if usadas_por_empresa:

        for empresa, codigos in usadas_por_empresa.items():

            mask = (
                df["Empresa / Filial"].str.startswith(empresa)
                & df["Produto"].isin(codigos)
            )

            df.loc[mask, "Conta"] = "Maquina Usada"

    df = df.drop(columns=["Empresa", "Filial"])

    # ------------------------------------------------------
    # ORGANIZA COLUNAS
    # ------------------------------------------------------

    colunas = [
        "Data Fechamento",
        "Empresa / Filial",
        "Conta",
        "Produto",
        "Descricao",
        "Saldo Atual",
        "Custo Total"
    ]

    df_final = df[colunas].copy()

    # ------------------------------------------------------
    # EXPORTAÇÃO
    # ------------------------------------------------------

    buffer = io.BytesIO()

    df_final.to_excel(buffer, index=False)

    buffer.seek(0)

    return df_final, buffer.getvalue()