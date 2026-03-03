import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # =========================
        # 1️⃣ LER TODOS XLSX DA PASTA 04_Movimento
        # =========================

        arquivos_mov = [
            f for f in z.namelist()
            if "04_Movimento/" in f and f.lower().endswith(".xlsx")
        ]

        if not arquivos_mov:
            raise Exception("Nenhum XLSX encontrado na pasta 04_Movimento.")

        lista_mov = []

        for nome_arquivo in arquivos_mov:

            with z.open(nome_arquivo) as arq:

                df = pd.read_excel(
                    arq,
                    dtype=str,
                    engine="openpyxl"
                )

            # Empresa vem do nome do arquivo
            nome_upper = nome_arquivo.upper()

            if "ROBOTICA" in nome_upper:
                empresa = "Robotica"
            elif "SERVICE" in nome_upper:
                empresa = "Service"
            else:
                empresa = "Indefinido"

            # =========================
            # PADRONIZA CAMPOS
            # =========================

            df["Codigo"] = df["Produto"].astype(str).str.strip()

            df["Qtd"] = pd.to_numeric(
                df["Quantidade"],
                errors="coerce"
            )

            df["Dt_Mov"] = pd.to_datetime(
                df["DT Emissao"],
                errors="coerce",
                dayfirst=True
            )

            df["Filial"] = df["Filial"].astype(str).str.strip().str.title()

            df["Empresa / Filial"] = empresa + " / " + df["Filial"]

            df["Descricao"] = df["Descr. Prod"]

            df_final_temp = df[
                [
                    "Empresa / Filial",
                    "Codigo",
                    "Descricao",
                    "Qtd",
                    "Dt_Mov"
                ]
            ].copy()

            lista_mov.append(df_final_temp)

        df_final = pd.concat(lista_mov, ignore_index=True)

        # Remove datas inválidas
        df_final = df_final[df_final["Dt_Mov"].notna()]

        # =========================
        # EXPORTAÇÃO
        # =========================

        buffer = io.BytesIO()
        df_final.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_final, buffer.getvalue()
