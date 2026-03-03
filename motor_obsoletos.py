import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # =========================
        # 1️⃣ LER CADASTRO DE EMPRESAS
        # =========================

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

        df_empresas["Empresa"] = df_empresas["Empresa"].str.strip()
        df_empresas["Filial"] = df_empresas["Filial"].str.strip()

        # Cria chave Empresa + CodigoFilial
        df_empresas["CHAVE"] = (
            df_empresas["Empresa"].str.upper() + "|" +
            df_empresas["Filial"]
        )

        # =========================
        # 2️⃣ LER MOVIMENTAÇÕES
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
            df["Filial"] = df["Filial"].astype(str).str.strip()

            df["Empresa"] = empresa

            # Cria chave para buscar nome filial
            df["CHAVE"] = (
                df["Empresa"].str.upper() + "|" +
                df["Filial"]
            )

            # Merge com cadastro de empresas
            df = df.merge(
                df_empresas[["CHAVE", "Nome Filial"]],
                on="CHAVE",
                how="left"
            )

            df["Empresa / Filial"] = (
                df["Empresa"] + " / " + df["Nome Filial"]
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

        # =========================
        # 3️⃣ ÚLTIMA MOVIMENTAÇÃO
        # =========================

        df_final = (
            df_mov
            .groupby(
                ["Empresa / Filial", "Produto", "ID_UNICO"],
                as_index=False
            )["DT Emissao"]
            .max()
            .rename(columns={
                "Produto": "Codigo",
                "DT Emissao": "Ult_Mov"
            })
        )

        # =========================
        # EXPORTAÇÃO
        # =========================

        buffer = io.BytesIO()
        df_final.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_final, buffer.getvalue()
