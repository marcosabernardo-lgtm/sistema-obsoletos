import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # =========================
        # 1️⃣ LER 05_EMPRESAS
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

        df_empresas["Mesclado"] = df_empresas["Mesclado"].str.strip()
        df_empresas["Empresa / Filial"] = df_empresas["Empresa / Filial"].str.strip()

        # =========================
        # 2️⃣ LER 01_ENTRADAS_SAIDAS
        # =========================

        arquivos_excel = [
            f for f in z.namelist()
            if "01_Entradas_Saidas/" in f and f.lower().endswith(".xlsx")
        ]

        if not arquivos_excel:
            raise Exception("Nenhum arquivo encontrado em 01_Entradas_Saidas")

        lista = []

        for nome_arquivo in arquivos_excel:

            with z.open(nome_arquivo) as arq:

                xl = pd.ExcelFile(arq)

                nome_upper = nome_arquivo.upper()

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
                            arq,
                            sheet_name=aba,
                            skiprows=1,  # 🔥 CORREÇÃO DO HEADER
                            dtype=str,
                            engine="openpyxl"
                        )

                        # Normaliza nomes das colunas
                        df.columns = df.columns.str.strip().str.upper()

                        df = df[[
                            "FILIAL",
                            "PRODUTO",
                            "DIGITACAO",
                            "ESTOQUE",
                            "QUANTIDADE"
                        ]].copy()

                        df["Tipo Movimento"] = tipo

                        # 🔹 TRATAMENTO NUMÉRICO
                        df["QUANTIDADE"] = (
                            df["QUANTIDADE"]
                            .astype(str)
                            .str.replace(".", "", regex=False)
                            .str.replace(",", ".", regex=False)
                        )

                        df["QUANTIDADE"] = pd.to_numeric(
                            df["QUANTIDADE"],
                            errors="coerce"
                        )

                        df["DIGITACAO"] = pd.to_datetime(
                            df["DIGITACAO"],
                            errors="coerce"
                        )

                        df = df[
                            (df["ESTOQUE"] == "S") &
                            (df["QUANTIDADE"] != 0)
                        ]

                        df["Produto"] = df["PRODUTO"].astype(str).str.strip()
                        df["Mesclado"] = empresa + " " + df["FILIAL"].astype(str).str.strip()

                        # 🔹 Merge com cadastro empresas
                        df = df.merge(
                            df_empresas[["Mesclado", "Empresa / Filial"]],
                            on="Mesclado",
                            how="left"
                        )

                        df["ID_UNICO"] = (
                            df["Empresa / Filial"] + "|" + df["Produto"]
                        )

                        df_temp = df[[
                            "Empresa / Filial",
                            "Produto",
                            "ID_UNICO",
                            "DIGITACAO",
                            "Tipo Movimento"
                        ]].copy()

                        lista.append(df_temp)

        df_mov = pd.concat(lista, ignore_index=True)

        # =========================
        # 3️⃣ CONSOLIDAÇÃO
        # =========================

        df_mov["DtEnt"] = df_mov["DIGITACAO"].where(df_mov["Tipo Movimento"] == "Entrada")
        df_mov["DtSai"] = df_mov["DIGITACAO"].where(df_mov["Tipo Movimento"] == "Saida")

        df_final = df_mov.groupby(
            ["Empresa / Filial", "Produto", "ID_UNICO"],
            as_index=False
        ).agg(
            Ult_Entrada=("DtEnt", "max"),
            Ult_Saida=("DtSai", "max")
        )

        # =========================
        # EXPORTAÇÃO
        # =========================

        buffer = io.BytesIO()
        df_final.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_final, buffer.getvalue()
