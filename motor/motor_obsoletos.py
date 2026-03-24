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


def executar_estoque(caminho_zip):

    with zipfile.ZipFile(caminho_zip, "r") as z:

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

        # --- CORREÇÃO: Limpa espaços nos cabeçalhos ---
        df.columns = df.columns.astype(str).str.strip()

        arquivos_usadas = [
            n for n in z.namelist()
            if "06_Usadas/" in n and n.lower().endswith(".xlsx")
        ]

        usadas_tipo_por_empresa = {}

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
            df_u["Codigo"] = df_u["Codigo"].astype(str).str.strip().str.replace(".0", "", regex=False)

            if "Tipo" in df_u.columns:
                # Normaliza o tipo das usadas para Title Case
                df_u["Tipo"] = df_u["Tipo"].astype(str).str.strip().str.title()
                tipo_map = dict(zip(df_u["Codigo"], df_u["Tipo"]))
            else:
                tipo_map = {c: "Maquina Usada" for c in df_u["Codigo"]}

            usadas_tipo_por_empresa[empresa] = tipo_map

    # --- CORREÇÃO: Tratamento do Tipo de Estoque ---
    df = df.rename(columns={
        "Valor Total": "Custo Total",
        "Código": "Produto",
        "Descrição": "Descricao",
        "Quantidade": "Saldo Atual"
    })

    if "Tipo de Estoque" in df.columns:
        df["Tipo de Estoque"] = df["Tipo de Estoque"].fillna("Não Informado").astype(str).str.strip().str.title()
    else:
        df["Tipo de Estoque"] = "Em Estoque"

    df["Vlr Unit"] = pd.to_numeric(df["Vlr Unit"], errors="coerce").fillna(0)
    df["Empresa"] = df["Empresa"].apply(normalizar_empresa)
    df["Filial"] = df["Filial"].astype(str).str.title()
    df["Empresa / Filial"] = df["Empresa"] + " / " + df["Filial"]
    df["Produto"] = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)
    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]
    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)
    
    # Normaliza a Conta original para Title
    if "Conta" in df.columns:
        df["Conta"] = df["Conta"].astype(str).str.strip().str.title()

    if usadas_tipo_por_empresa:
        for empresa, tipo_map in usadas_tipo_por_empresa.items():
            for codigo, tipo in tipo_map.items():
                mask = (
                    df["Empresa / Filial"].str.startswith(empresa) &
                    (df["Produto"] == codigo)
                )
                df.loc[mask, "Conta"] = tipo

    df = df.drop(columns=["Empresa", "Filial"])

    colunas = df.columns.tolist()
    nova_ordem = ["Data Fechamento", "Empresa / Filial"]
    demais = [c for c in colunas if c not in nova_ordem]

    return df[nova_ordem + demais]


# ==========================================================
# MOVIMENTAÇÕES (Sem alterações necessárias aqui)
# ==========================================================

def executar_movimentacoes(caminho_zip):

    with zipfile.ZipFile(caminho_zip, "r") as z:

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

            df["DT Emissao"] = pd.to_datetime(df["DT Emissao"], errors="coerce", dayfirst=True)
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
# ENTRADAS / SAÍDAS (Sem alterações necessárias aqui)
# ==========================================================

def executar_entradas_saidas(caminho_zip):

    with zipfile.ZipFile(caminho_zip, "r") as z:

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
                    df = pd.read_excel(xl, sheet_name=aba, skiprows=1, dtype=str, engine="openpyxl")
                    df.columns = df.columns.str.strip().str.upper()
                    if all(col in df.columns for col in ["FILIAL", "PRODUTO", "DIGITACAO", "ESTOQUE"]):
                        df = df[["FILIAL", "PRODUTO", "DIGITACAO", "ESTOQUE"]].copy()
                        df["DIGITACAO"] = pd.to_datetime(df["DIGITACAO"], errors="coerce")
                        df = df[df["ESTOQUE"] == "S"]
                        df["Produto"] = df["PRODUTO"].astype(str).str.strip()
                        df["Mesclado"] = empresa + " " + df["FILIAL"].astype(str).str.strip()
                        df = df.merge(df_empresas[["Mesclado", "Empresa / Filial"]], on="Mesclado", how="left")
                        df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]
                        if tipo == "Entrada":
                            df["DtEnt"] = df["DIGITACAO"]
                            df["DtSai"] = pd.NaT
                        else:
                            df["DtEnt"] = pd.NaT
                            df["DtSai"] = df["DIGITACAO"]
                        lista.append(df[["ID_UNICO", "DtEnt", "DtSai"]])

        if not lista:
            return pd.DataFrame(columns=["ID_UNICO", "Ult_Entrada", "Ult_Saida"])
            
        df_all = pd.concat(lista, ignore_index=True)

        return df_all.groupby("ID_UNICO", as_index=False).agg(
            Ult_Entrada=("DtEnt", "max"),
            Ult_Saida=("DtSai", "max")
        )


# ==========================================================
# MOTOR FINAL
# ==========================================================

def executar_motor(caminho_zip):

    df_estoque = executar_estoque(caminho_zip)
    df_mov = executar_movimentacoes(caminho_zip)
    df_es = executar_entradas_saidas(caminho_zip)

    df_final = df_estoque.merge(df_mov, on="ID_UNICO", how="left")
    df_final = df_final.merge(df_es, on="ID_UNICO", how="left")

    df_final["Ult_Movimentacao"] = df_final[["Ult_Mov", "Ult_Entrada", "Ult_Saida"]].max(axis=1)
    df_final["Ult_Movimentacao"] = pd.to_datetime(df_final["Ult_Movimentacao"], errors="coerce")

    def origem(row):
        if row["Ult_Movimentacao"] == row["Ult_Saida"]:
            return "Ult_Saida"
        elif row["Ult_Movimentacao"] == row["Ult_Entrada"]:
            return "Ult_Entrada"
        elif row["Ult_Movimentacao"] == row["Ult_Mov"]:
            return "Ult_Mov"
        return None

    df_final["Origem Mov"] = df_final.apply(origem, axis=1)
    df_final = df_final.drop(columns=["Ult_Mov", "Ult_Entrada", "Ult_Saida"])

    # --- CORREÇÃO: Normalização Title Case ---
    df_final["Tipo de Estoque"] = df_final["Tipo de Estoque"].astype(str).str.title()
    
    CONTA_CORRECOES = {
        "MR":                  "Material Revenda",
        "MATERIAL REVENDA":    "Material Revenda",
        "MATERIAL DE REVENDA": "Material De Revenda",
    }
    df_final["Conta"] = df_final["Conta"].astype(str).str.strip().str.upper().map(
        lambda x: CONTA_CORRECOES.get(x, x)
    ).str.title()
    
    df_final = df_final.drop(columns=["ID_UNICO"])

    DataBase = pd.to_datetime(df_final["Data Fechamento"].iloc[0])

    df_final["Dias Sem Mov"] = (DataBase - df_final["Ult_Movimentacao"]).dt.days.fillna(9999)

    df_final["Meses Ult Mov"] = np.where(
        df_final["Ult_Movimentacao"].notna(),
        (DataBase.year - df_final["Ult_Movimentacao"].dt.year) * 12 +
        (DataBase.month - df_final["Ult_Movimentacao"].dt.month),
        np.nan
    )

    # --- CORREÇÃO: Ajuste do Status para bater com o Title Case ---
    # Agora verificamos "Em Fabricacao" ou "Em Fabricação" (depende de como está no Excel)
    df_final["Status Estoque"] = np.where(
        df_final["Tipo de Estoque"].str.contains("Fabric", case=False), 
        "Até 6 meses",
        np.where(
            df_final["Ult_Movimentacao"].isna() | (df_final["Meses Ult Mov"] > 6),
            "Obsoleto",
            "Até 6 meses"
        )
    )

    def status_mov(row):
        # Busca flexível por Fabricação
        if "Fabric" in str(row["Tipo de Estoque"]):
            return "Até 6 meses"
        if pd.isna(row["Meses Ult Mov"]):
            return "Sem Movimento"
        if row["Meses Ult Mov"] <= 6:
            return "Até 6 meses"
        if row["Meses Ult Mov"] <= 12:
            return "Até 1 ano"
        if row["Meses Ult Mov"] <= 24:
            return "+ 1 ano"
        return "+ 2 anos"

    df_final["Status do Movimento"] = df_final.apply(status_mov, axis=1)

    def formatar(row):
        if "Fabric" in str(row["Tipo de Estoque"]):
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