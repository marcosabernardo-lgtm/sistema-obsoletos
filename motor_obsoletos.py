import pandas as pd
import zipfile
import io


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


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # =========================
        # 1️⃣ LEITURA ESTOQUE (SEM ALTERAÇÃO)
        # =========================

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

        # =========================
        # 2️⃣ LEITURA MOVIMENTAÇÕES (SOMENTE PARA GERAR ULT_MOV)
        # =========================

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
            df["Filial"] = df["Filial"].astype(str).str.title()

            df["Empresa / Filial"] = empresa + " / " + df["Filial"]

            df["ID_UNICO"] = (
                df["Empresa / Filial"] + "|" + df["Produto"]
            )

            df["DT Emissao"] = pd.to_datetime(
                df["DT Emissao"],
                errors="coerce",
                dayfirst=True
            )

            df_temp = df[["ID_UNICO", "DT Emissao"]].copy()

            lista_mov.append(df_temp)

        if lista_mov:
            df_mov = pd.concat(lista_mov, ignore_index=True)
            df_mov = df_mov[df_mov["DT Emissao"].notna()]

            df_ult_mov = (
                df_mov
                .groupby("ID_UNICO", as_index=False)["DT Emissao"]
                .max()
                .rename(columns={"DT Emissao": "Ult_Mov"})
            )
        else:
            df_ult_mov = pd.DataFrame(columns=["ID_UNICO", "Ult_Mov"])

        # =========================
        # 3️⃣ MERGE SIMPLES
        # =========================

        df_final = df_estoque.merge(
            df_ult_mov,
            on="ID_UNICO",
            how="left"
        )

        # =========================
        # ORGANIZA COLUNAS (MANTIDO)
        # =========================

        colunas = df_final.columns.tolist()
        nova_ordem = ["Data Fechamento", "Empresa / Filial"]
        demais = [c for c in colunas if c not in nova_ordem]

        df_final = df_final[nova_ordem + demais]

        buffer = io.BytesIO()
        df_final.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_final, buffer.getvalue()
