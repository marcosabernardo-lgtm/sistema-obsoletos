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


def executar_estoque(z):

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

    # ==========================================================
    # MAQUINAS USADAS — lê os CSVs de 06_Usadas/ e marca a Conta
    # ==========================================================
    arquivos_usadas = [
        n for n in z.namelist()
        if "06_Usadas/" in n and n.lower().endswith(".csv")
    ]

    if arquivos_usadas:
        lista_usadas = []
        for nome in arquivos_usadas:
            with z.open(nome) as f:
                conteudo = f.read().decode("utf-8", errors="ignore")
            df_csv = pd.read_csv(
                io.StringIO(conteudo),
                dtype=str,
                sep=",",
                quotechar='"',
                engine="python"
            )
            df_csv.columns = df_csv.columns.str.strip()
            lista_usadas.append(df_csv)

        df_usadas = pd.concat(lista_usadas, ignore_index=True)

        # Busca flexível pela coluna de código (ignora acentos e espaços)
        col_codigo = next(
            (c for c in df_usadas.columns
             if c.strip().upper().replace("Ó", "O").replace("Ô", "O") in ["CODIGO", "CÓDIGO", "COD", "CODPROD"]),
            df_usadas.columns[0]  # fallback: usa a primeira coluna
        )

        codigos_usadas = set(
            df_usadas[col_codigo].astype(str).str.strip().str.replace(".0", "", regex=False)
        )

        df.loc[df["Produto"].isin(codigos_usadas), "Conta"] = "Maquina Usada"

    # ==========================================================

    df = df.drop(columns=["Empresa", "Filial"])

    colunas = df.columns.tolist()
    nova_ordem = ["Data Fechamento", "Empresa / Filial"]
    demais = [c for c in colunas if c not in nova_ordem]

    return df[nova_ordem + demais]


# ==========================================================
# MOVIMENTAÇÕES
# ==========================================================

def executar_movimentacoes(z, df_empresas):

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

def executar_entradas_saidas(z, df_empresas):

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

    # ZIP aberto uma única vez — compartilhado entre todas as funções
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

        df_estoque = executar_estoque(z)
        df_mov     = executar_movimentacoes(z, df_empresas)
        df_es      = executar_entradas_saidas(z, df_empresas)

    # Merges
    df_final = df_estoque.merge(df_mov, on="ID_UNICO", how="left")
    df_final = df_final.merge(df_es,   on="ID_UNICO", how="left")

    # Última movimentação
    df_final["Ult_Movimentacao"] = df_final[
        ["Ult_Mov", "Ult_Entrada", "Ult_Saida"]
    ].max(axis=1)

    # Origem da movimentação — vetorizado com np.select
    cond_saida   = df_final["Ult_Movimentacao"] == df_final["Ult_Saida"]
    cond_entrada = df_final["Ult_Movimentacao"] == df_final["Ult_Entrada"]
    cond_mov     = df_final["Ult_Movimentacao"] == df_final["Ult_Mov"]

    df_final["Origem Mov"] = np.select(
        [cond_saida, cond_entrada, cond_mov],
        ["Ult_Saida", "Ult_Entrada", "Ult_Mov"],
        default=None
    )

    df_final = df_final.drop(columns=["Ult_Mov", "Ult_Entrada", "Ult_Saida"])

    # Normaliza Tipo de Estoque em maiúsculo ANTES das comparações
    df_final["Tipo de Estoque"] = df_final["Tipo de Estoque"].astype(str).str.strip().str.upper()
    df_final["Conta"] = df_final["Conta"].str.title()
    df_final = df_final.drop(columns=["ID_UNICO"])

    # ==========================================================
    # BLOCO FINAL
    # ==========================================================

    DataBase = pd.to_datetime(df_final["Data Fechamento"].iloc[0])

    df_final["Dias Sem Mov"] = (
        DataBase - df_final["Ult_Movimentacao"]
    ).dt.days.fillna(9999)

    df_final["Meses Ult Mov"] = np.where(
        df_final["Ult_Movimentacao"].notna(),
        (DataBase.year  - df_final["Ult_Movimentacao"].dt.year)  * 12 +
        (DataBase.month - df_final["Ult_Movimentacao"].dt.month),
        np.nan
    )

    eh_fabricacao = df_final["Tipo de Estoque"] == "EM FABRICACAO"

    # Status Estoque — vetorizado
    df_final["Status Estoque"] = np.where(
        eh_fabricacao,
        "Até 6 meses",
        np.where(df_final["Dias Sem Mov"] > 180, "Obsoleto", "Até 6 meses")
    )

    # Status do Movimento — vetorizado com np.select
    meses = df_final["Meses Ult Mov"]
    df_final["Status do Movimento"] = np.select(
        [
            eh_fabricacao,
            meses.isna(),
            meses <= 6,
            meses <= 12,
            meses <= 24,
        ],
        [
            "Até 6 meses",
            "Sem Movimento",
            "Até 6 meses",
            "Até 1 ano",
            "Até 2 anos",
        ],
        default="+ 2 anos"
    )

    # Ano Meses Dias — vetorizado
    dias_total  = (DataBase - df_final["Ult_Movimentacao"]).dt.days
    anos        = (dias_total // 365).astype("Int64")
    meses_calc  = ((dias_total % 365) // 30).astype("Int64")
    dias_rest   = ((dias_total % 365) % 30).astype("Int64")

    texto_tempo = (
        anos.astype(str)       + " anos " +
        meses_calc.astype(str) + " meses " +
        dias_rest.astype(str)  + " dias"
    )

    df_final["Ano Meses Dias"] = np.select(
        [
            eh_fabricacao,
            df_final["Ult_Movimentacao"].isna(),
        ],
        [
            "Em fabricação",
            "Sem movimento",
        ],
        default=texto_tempo
    )

    # Aplica title no Tipo de Estoque APÓS as comparações
    df_final["Tipo de Estoque"] = df_final["Tipo de Estoque"].str.title()

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
