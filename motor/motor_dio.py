import pandas as pd
import zipfile
import io
import numpy as np
import os


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
# SALDO DE ESTOQUE — lê do ZIP do motor_estoque
# ==========================================================

def ler_saldo_estoque(caminho_zip_estoque):
    with zipfile.ZipFile(caminho_zip_estoque, "r") as z:

        arquivo = next(
            (n for n in z.namelist()
             if "02_Estoque_Atual" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo:
            raise Exception("Arquivo 02_Estoque_Atual não encontrado no ZIP de estoque")

        with z.open(arquivo) as f:
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

    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)
    df["Vlr Unit"] = pd.to_numeric(df.get("Vlr Unit", 0), errors="coerce").fillna(0)
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"], errors="coerce")
    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]

    return df[[
        "Data Fechamento", "Empresa / Filial", "Produto",
        "Descricao", "Saldo Atual", "Custo Total", "Vlr Unit", "ID_UNICO"
    ]]


# ==========================================================
# SAÍDAS — 01_Entradas_Saidas aba SAIDA
# ==========================================================

def ler_saidas(caminho_zip_obsoletos):
    with zipfile.ZipFile(caminho_zip_obsoletos, "r") as z:

        arquivo_empresas = next(
            (n for n in z.namelist()
             if "05_Empresas" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_empresas:
            return pd.DataFrame(columns=["ID_UNICO", "Data", "Qtd_Saida"])

        with z.open(arquivo_empresas) as f:
            df_empresas = pd.read_excel(f, dtype=str, engine="openpyxl")

        df_empresas["Mesclado"] = df_empresas["Mesclado"].str.strip()
        df_empresas["Empresa / Filial"] = df_empresas["Empresa / Filial"].str.strip()

        arquivos = [
            n for n in z.namelist()
            if "01_Entradas_Saidas/" in n and n.lower().endswith(".xlsx")
        ]

        lista = []

        for nome in arquivos:
            with z.open(nome) as arq:
                arquivo_bytes = io.BytesIO(arq.read())

            xl = pd.ExcelFile(arquivo_bytes, engine="openpyxl")
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

            if "SAIDA" not in xl.sheet_names:
                continue

            df = pd.read_excel(
                xl, sheet_name="SAIDA", skiprows=1,
                dtype=str, engine="openpyxl"
            )
            df.columns = df.columns.str.strip().str.upper()

            if "ESTOQUE" in df.columns:
                df = df[df["ESTOQUE"] == "S"]

            col_qtd = next(
                (c for c in df.columns if "QUANT" in c or "QTD" in c or "QT " in c),
                None
            )

            df["Data"] = pd.to_datetime(df.get("DIGITACAO", pd.NaT), errors="coerce")
            df["Produto"] = df["PRODUTO"].astype(str).str.strip()
            df["Mesclado"] = empresa + " " + df["FILIAL"].astype(str).str.strip()

            df = df.merge(
                df_empresas[["Mesclado", "Empresa / Filial"]],
                on="Mesclado", how="left"
            )

            df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]
            df["Qtd_Saida"] = pd.to_numeric(df[col_qtd], errors="coerce").fillna(0).abs() if col_qtd else 1

            lista.append(df[["ID_UNICO", "Data", "Qtd_Saida"]])

    if not lista:
        return pd.DataFrame(columns=["ID_UNICO", "Data", "Qtd_Saida"])

    return pd.concat(lista, ignore_index=True)


# ==========================================================
# MOVIMENTAÇÕES — 04_Movimento
# ==========================================================

def ler_movimentacoes(caminho_zip_obsoletos):
    with zipfile.ZipFile(caminho_zip_obsoletos, "r") as z:

        arquivo_empresas = next(
            (n for n in z.namelist()
             if "05_Empresas" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_empresas:
            return pd.DataFrame(columns=["ID_UNICO", "Data", "Qtd_Saida"])

        with z.open(arquivo_empresas) as f:
            df_empresas = pd.read_excel(f, dtype=str, engine="openpyxl")

        df_empresas["Mesclado"] = df_empresas["Mesclado"].str.strip()
        df_empresas["Empresa / Filial"] = df_empresas["Empresa / Filial"].str.strip()

        arquivos = [
            n for n in z.namelist()
            if "04_Movimento/" in n and n.lower().endswith(".xlsx")
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

            df.columns = df.columns.str.strip().str.upper()

            col_qtd = next(
                (c for c in df.columns if "QUANT" in c or "QTD" in c or "QT " in c),
                None
            )
            col_data = next(
                (c for c in df.columns if "EMISSAO" in c or "DATA" in c or "DT" in c),
                None
            )

            df["Produto"] = df["PRODUTO"].astype(str).str.strip()
            df["Mesclado"] = empresa + " " + df["FILIAL"].astype(str).str.strip()

            df = df.merge(
                df_empresas[["Mesclado", "Empresa / Filial"]],
                on="Mesclado", how="left"
            )

            df["Data"] = pd.to_datetime(
                df[col_data] if col_data else pd.NaT,
                errors="coerce", dayfirst=True
            )

            df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]
            df["Qtd_Saida"] = pd.to_numeric(df[col_qtd], errors="coerce").fillna(0).abs() if col_qtd else 1

            lista.append(df[["ID_UNICO", "Data", "Qtd_Saida"]])

    if not lista:
        return pd.DataFrame(columns=["ID_UNICO", "Data", "Qtd_Saida"])

    return pd.concat(lista, ignore_index=True)


# ==========================================================
# MOTOR DIO — FUNÇÃO PRINCIPAL
# ==========================================================

def executar_motor_dio(caminho_zip_estoque, pasta_zips_obsoletos):
    """
    Calcula o DIO (Days Inventory Outstanding) por produto.

    Parâmetros:
        caminho_zip_estoque  : caminho do ZIP do motor_estoque
        pasta_zips_obsoletos : pasta com os ZIPs mensais do motor_obsoletos

    Retorna:
        df_final : DataFrame com DIO por produto
        buffer   : bytes do Excel exportado
    """

    # ----------------------------------------------------------
    # 1. SALDO DO ÚLTIMO FECHAMENTO
    # ----------------------------------------------------------

    df_saldo_full = ler_saldo_estoque(caminho_zip_estoque)

    data_ultimo_fechamento = df_saldo_full["Data Fechamento"].max()
    data_inicio_janela = data_ultimo_fechamento - pd.DateOffset(months=12)

    df_saldo = df_saldo_full[
        df_saldo_full["Data Fechamento"] == data_ultimo_fechamento
    ].copy()

    # ----------------------------------------------------------
    # 2. CONSUMO — lê todos os ZIPs da pasta de obsoletos
    # ----------------------------------------------------------

    lista_saidas = []
    lista_movs = []

    zips = sorted([
        os.path.join(pasta_zips_obsoletos, f)
        for f in os.listdir(pasta_zips_obsoletos)
        if f.lower().endswith(".zip")
    ])

    for zip_path in zips:
        try:
            lista_saidas.append(ler_saidas(zip_path))
        except Exception:
            pass
        try:
            lista_movs.append(ler_movimentacoes(zip_path))
        except Exception:
            pass

    consumo_parts = [p for p in lista_saidas + lista_movs if not p.empty]

    dias_janela = (data_ultimo_fechamento - data_inicio_janela).days

    if not consumo_parts:
        df_saldo["Consumo_12m"] = 0
        df_saldo["Consumo_Diario"] = 0
        df_saldo["DIO"] = np.inf
    else:
        df_consumo = pd.concat(consumo_parts, ignore_index=True)
        df_consumo = df_consumo[
            (df_consumo["Data"] >= data_inicio_janela) &
            (df_consumo["Data"] <= data_ultimo_fechamento)
        ].drop_duplicates()

        df_cons = (
            df_consumo
            .groupby("ID_UNICO", as_index=False)["Qtd_Saida"]
            .sum()
            .rename(columns={"Qtd_Saida": "Consumo_12m"})
        )
        df_cons["Consumo_Diario"] = df_cons["Consumo_12m"] / dias_janela

        df_saldo = df_saldo.merge(df_cons, on="ID_UNICO", how="left")
        df_saldo["Consumo_12m"] = df_saldo["Consumo_12m"].fillna(0)
        df_saldo["Consumo_Diario"] = df_saldo["Consumo_Diario"].fillna(0)

        df_saldo["DIO"] = np.where(
            df_saldo["Consumo_Diario"] > 0,
            df_saldo["Saldo Atual"] / df_saldo["Consumo_Diario"],
            np.inf
        )

    # ----------------------------------------------------------
    # 3. CATEGORIZA E FORMATA
    # ----------------------------------------------------------

    ordem_faixas = [
        "Até 30 dias",
        "31–90 dias",
        "91–180 dias",
        "181–365 dias",
        "+ 1 ano",
        "Sem consumo"
    ]

    def categorizar_dio(dio):
        if dio == np.inf or pd.isna(dio):
            return "Sem consumo"
        if dio <= 30:
            return "Até 30 dias"
        if dio <= 90:
            return "31–90 dias"
        if dio <= 180:
            return "91–180 dias"
        if dio <= 365:
            return "181–365 dias"
        return "+ 1 ano"

    def formatar_dio(dio):
        if dio == np.inf or pd.isna(dio):
            return "Sem consumo"
        dias = int(round(dio))
        anos = dias // 365
        meses = (dias % 365) // 30
        d = (dias % 365) % 30
        partes = []
        if anos:
            partes.append(f"{anos} ano{'s' if anos > 1 else ''}")
        if meses:
            partes.append(f"{meses} {'meses' if meses > 1 else 'mês'}")
        if d or not partes:
            partes.append(f"{d} dia{'s' if d != 1 else ''}")
        return " ".join(partes)

    df_saldo["Faixa DIO"] = df_saldo["DIO"].apply(categorizar_dio)
    df_saldo["DIO_Formatado"] = df_saldo["DIO"].apply(formatar_dio)

    # ----------------------------------------------------------
    # 4. MONTA RESULTADO FINAL
    # ----------------------------------------------------------

    colunas = [
        "Data Fechamento",
        "Empresa / Filial",
        "Produto",
        "Descricao",
        "Saldo Atual",
        "Custo Total",
        "Vlr Unit",
        "Consumo_12m",
        "Consumo_Diario",
        "DIO",
        "DIO_Formatado",
        "Faixa DIO",
    ]

    df_final = df_saldo[
        [c for c in colunas if c in df_saldo.columns]
    ].sort_values(
        ["Empresa / Filial", "DIO"],
        ascending=[True, True],
        na_position="last"
    ).reset_index(drop=True)

    # ----------------------------------------------------------
    # 5. SALVA PARQUET em data/dio
    # ----------------------------------------------------------

    pasta_dio = "data/dio"
    os.makedirs(pasta_dio, exist_ok=True)

    data_str = data_ultimo_fechamento.strftime("%Y-%m-%d")
    caminho_parquet = os.path.join(pasta_dio, f"{data_str}.parquet")
    df_final.to_parquet(caminho_parquet, index=False)

    # ----------------------------------------------------------
    # 6. EXPORTA EXCEL
    # ----------------------------------------------------------

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()