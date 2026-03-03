import pandas as pd
import zipfile
import io


# =========================
# ESTOQUE (INALTERADO)
# =========================

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
            df_estoque = pd.read_excel(
                f,
                sheet_name="Detalhado",
                dtype={"Código": str},
                engine="openpyxl"
            )

        df_estoque = df_estoque.rename(columns={
            "Valor Total": "Custo Total",
            "Código": "Produto",
            "Descrição": "Descricao",
            "Quantidade": "Saldo Atual"
        })

        df_estoque["Empresa"] = df_estoque["Empresa"].apply(normalizar_empresa)
        df_estoque["Filial"] = df_estoque["Filial"].astype(str).str.title()

        df_estoque["Empresa / Filial"] = (
            df_estoque["Empresa"] + " / " + df_estoque["Filial"]
        )

        df_estoque["Produto"] = (
            df_estoque["Produto"]
            .astype(str)
            .str.strip()
            .str.replace(".0", "", regex=False)
        )

        df_estoque["ID_UNICO"] = (
            df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]
        )

        df_estoque["Saldo Atual"] = pd.to_numeric(
            df_estoque["Saldo Atual"], errors="coerce"
        )

        df_estoque["Custo Total"] = pd.to_numeric(
            df_estoque["Custo Total"], errors="coerce"
        )

        df_estoque = df_estoque.drop(columns=["Empresa", "Filial"])

        colunas = df_estoque.columns.tolist()
        nova_ordem = ["Data Fechamento", "Empresa / Filial"]
        demais = [c for c in colunas if c not in nova_ordem]

        df_final = df_estoque[nova_ordem + demais]

        return df_final


# =========================
# MOVIMENTAÇÕES (INALTERADO)
# =========================

def executar_movimentacoes(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        arquivo_empresas = next(
            (n for n in z.namelist()
             if "05_Empresas" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_empresas:
            raise Exception("Arquivo 05_Empresas não encontrado.")

        with z.open(arquivo_empresas) as f:
            df_empresas = pd.read_excel(
                f,
                dtype=str,
                engine="openpyxl"
            )

        df_empresas["Mesclado"] = df_empresas["Mesclado"].str.strip()
        df_empresas["Empresa / Filial"] = df_empresas["Empresa / Filial"].str.strip()

        arquivos_mov = [
            f for f in z.namelist()
            if "04_Movimento/" in f and f.lower().endswith(".xlsx")
        ]

        lista_mov = []

        for nome_arquivo in arquivos_mov:

            with z.open(nome_arquivo) as arq:

                df = pd.read_excel(
                    arq,
                    dtype=str,
                    engine="openpyxl"
                )

            nome_upper = nome_arquivo.upper()

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

            df["ID_UNICO"] = (
                df["Empresa / Filial"] + "|" + df["Produto"]
            )

            df_temp = df[
                ["Empresa / Filial", "Produto", "ID_UNICO", "DT Emissao"]
            ].copy()

            lista_mov.append(df_temp)

        if not lista_mov:
            raise Exception("Nenhuma movimentação encontrada.")

        df_mov = pd.concat(lista_mov, ignore_index=True)
        df_mov = df_mov[df_mov["DT Emissao"].notna()]

        df_final = (
            df_mov
            .groupby(
                ["Empresa / Filial", "Produto", "ID_UNICO"],
                as_index=False
            )["DT Emissao"]
            .max()
            .rename(columns={
                "DT Emissao": "Ult_Mov"
            })
        )

        return df_final


# =========================
# FUNÇÃO FINAL UNIFICADA
# =========================

def executar_motor(uploaded_file):

    df_estoque = executar_estoque(uploaded_file)
    df_mov = executar_movimentacoes(uploaded_file)

    df_mov_reduzido = df_mov[["ID_UNICO", "Ult_Mov"]]

    df_final = df_estoque.merge(
        df_mov_reduzido,
        on="ID_UNICO",
        how="left"
    )

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
