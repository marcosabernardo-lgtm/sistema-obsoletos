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
# ENTRADAS / SAÍDAS
# ==========================================================

def executar_entradas_saidas(uploaded_file):

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
            if "01_Entradas_Saidas/" in f and f.lower().endswith(".xlsx")
        ]

        lista = []

        for nome in arquivos:

            with z.open(nome) as arq:
                arquivo_bytes = io.BytesIO(arq.read())

            xl = pd.ExcelFile(arquivo_bytes)

            nome_upper = nome.upper()

            if "ROBOTICA" in nome_upper:
                empresa = "Robotica"
            elif "SERVICE" in nome_upper:
                empresa = "Service"
            elif "TOOLS" in nome_upper:
                empresa = "Tools"
            elif "MAQUINAS" in nome_upper:
                empresa = "Maquinas"
            else:
                continue

            for aba, tipo in [("ENTRADA", "Entrada"), ("SAIDA", "Saida")]:

                if aba in xl.sheet_names:

                    df = pd.read_excel(
                        xl,
                        sheet_name=aba,
                        skiprows=1,
                        dtype=str,
                        engine="openpyxl"
                    )

                    df.columns = df.columns.str.strip().str.upper()

                    df = df[[
                        "FILIAL",
                        "PRODUTO",
                        "DIGITACAO",
                        "ESTOQUE"
                    ]].copy()

                    df["DIGITACAO"] = pd.to_datetime(df["DIGITACAO"], errors="coerce")
                    df = df[df["ESTOQUE"] == "S"]

                    df["Produto"] = df["PRODUTO"].astype(str).str.strip()
                    df["Mesclado"] = empresa + " " + df["FILIAL"].astype(str).str.strip()

                    df = df.merge(
                        df_empresas[["Mesclado", "Empresa / Filial"]],
                        on="Mesclado",
                        how="left"
                    )

                    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]

                    if tipo == "Entrada":
                        df["DtEnt"] = df["DIGITACAO"]
                        df["DtSai"] = pd.NaT
                    else:
                        df["DtEnt"] = pd.NaT
                        df["DtSai"] = df["DIGITACAO"]

                    lista.append(df[["ID_UNICO", "DtEnt", "DtSai"]])

        df_all = pd.concat(lista, ignore_index=True)

        return df_all.groupby("ID_UNICO", as_index=False).agg(
            Ult_Entrada=("DtEnt", "max"),
            Ult_Saida=("DtSai", "max")
        )


# ==========================================================
# MOTOR FINAL
# ==========================================================

def executar_motor(uploaded_file):

    df_estoque = executar_estoque(uploaded_file)
    df_mov = executar_movimentacoes(uploaded_file)
    df_es = executar_entradas_saidas(uploaded_file)

    df_final = df_estoque.merge(df_mov, on="ID_UNICO", how="left")
    df_final = df_final.merge(df_es, on="ID_UNICO", how="left")

    df_final["Ult_Movimentacao"] = df_final[
        ["Ult_Mov", "Ult_Entrada", "Ult_Saida"]
    ].max(axis=1)

    def origem(row):
        if row["Ult_Movimentacao"] == row["Ult_Saida"]:
            return "Ult_Saida"
        elif row["Ult_Movimentacao"] == row["Ult_Entrada"]:
            return "Ult_Entrada"
        elif row["Ult_Movimentacao"] == row["Ult_Mov"]:
            return "Ult_Mov"
        return None

    df_final["Origem Mov"] = df_final.apply(origem, axis=1)

    df_final = df_final.drop(
        columns=["Ult_Mov", "Ult_Entrada", "Ult_Saida"]
    )

    # Ajustes pedidos
    df_final["Tipo de Estoque"] = df_final["Tipo de Estoque"].str.title()
    df_final["Conta"] = df_final["Conta"].str.title()
    df_final = df_final.drop(columns=["ID_UNICO"])


    # ==========================================================
    # BLOCO FINAL (APENAS ACRESCENTADO)
    # ==========================================================

    DataBase = pd.to_datetime(df_final["Data Fechamento"].iloc[0])

    df_final["Dias Sem Mov"] = (
        DataBase - df_final["Ult_Movimentacao"]
    ).dt.days.fillna(9999)

    df_final["Meses Ult Mov"] = np.where(
        df_final["Ult_Movimentacao"].notna(),
        (DataBase.year - df_final["Ult_Movimentacao"].dt.year) * 12 +
        (DataBase.month - df_final["Ult_Movimentacao"].dt.month),
        np.nan
    )

    df_final["Status Estoque"] = np.where(
        df_final["Tipo de Estoque"] == "EM FABRICACAO",
        "Até 6 meses",
        np.where(df_final["Dias Sem Mov"] > 180, "Obsoleto", "Até 6 meses")
    )

    def status_mov(row):
        if row["Tipo de Estoque"] == "EM FABRICACAO":
            return "Até 6 meses"
        if pd.isna(row["Meses Ult Mov"]):
            return "Sem Movimento"
        if row["Meses Ult Mov"] <= 6:
            return "Até 6 meses"
        if row["Meses Ult Mov"] <= 12:
            return "Até 1 ano"
        if row["Meses Ult Mov"] <= 24:
            return "Até 2 anos"
        return "+ 2 anos"

    df_final["Status do Movimento"] = df_final.apply(status_mov, axis=1)

    def formatar(row):
        if row["Tipo de Estoque"] == "EM FABRICACAO":
            return "Em fabricação"
        if pd.isna(row["Ult_Movimentacao"]):
            return "Sem movimento"

        dias = (DataBase - row["Ult_Movimentacao"]).days
        anos = dias // 365
        meses = (dias % 365) // 30
        dias_rest = (dias % 365) % 30

        return f"{anos} anos {meses} meses {dias_rest} dias"

    df_final["Ano Meses Dias"] = df_final.apply(formatar, axis=1)

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
