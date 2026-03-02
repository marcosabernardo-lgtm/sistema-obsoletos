import pandas as pd
import zipfile
import io
import time
import unicodedata


def normalizar_coluna(col):
    col = str(col).strip().upper()
    col = unicodedata.normalize("NFKD", col).encode("ASCII", "ignore").decode("ASCII")
    return col


def executar_motor(uploaded_file):

    inicio = time.time()

    with zipfile.ZipFile(uploaded_file) as z:

        # =====================================================
        # 1️⃣ MATRIZ 05_EMPRESAS
        # =====================================================

        arquivo_matriz = next(
            (n for n in z.namelist()
             if "05_Empresas" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_matriz:
            raise Exception("05_Empresas não encontrado no ZIP")

        with z.open(arquivo_matriz) as f:
            df_matriz = pd.read_excel(f, engine="openpyxl")

        df_matriz.columns = [normalizar_coluna(c) for c in df_matriz.columns]

        # Esperado: MESCLADO | EMPRESA / FILIAL
        df_matriz = df_matriz[["MESCLADO", "EMPRESA / FILIAL"]]

        # =====================================================
        # 2️⃣ ENTRADAS / SAÍDAS
        # =====================================================

        lista_mov = []

        arquivos_excel = [
            n for n in z.namelist()
            if "01_Entradas_Saidas" in n and n.endswith(".xlsx")
        ]

        for arq in arquivos_excel:

            # Nome empresa vem do arquivo
            empresa_arquivo = arq.split("_")[1]

            with z.open(arq) as f:

                xls = pd.ExcelFile(f, engine="openpyxl")

                for aba in ["ENTRADA", "SAIDA"]:

                    if aba not in xls.sheet_names:
                        continue

                    df_temp = pd.read_excel(
                        xls,
                        sheet_name=aba,
                        engine="openpyxl"
                    )

                    # Normaliza nomes das colunas
                    df_temp.columns = [normalizar_coluna(c) for c in df_temp.columns]

                    if "ESTOQUE" not in df_temp.columns:
                        continue

                    df_temp = df_temp[df_temp["ESTOQUE"] == "S"]

                    if df_temp.empty:
                        continue

                    # Cria chave Mesclado (igual padrão anterior)
                    df_temp["FILIAL"] = df_temp["FILIAL"].astype(str).str.strip()

                    df_temp["MESCLADO"] = (
                        empresa_arquivo.upper() + " " + df_temp["FILIAL"]
                    )

                    # Merge com matriz
                    df_temp = df_temp.merge(
                        df_matriz,
                        on="MESCLADO",
                        how="left"
                    )

                    df_temp = df_temp[df_temp["EMPRESA / FILIAL"].notna()]

                    if df_temp.empty:
                        continue

                    # Produto
                    df_temp["PRODUTO"] = (
                        df_temp["PRODUTO"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                    )

                    # Data
                    df_temp["DT_EMISSAO"] = pd.to_datetime(
                        df_temp["DIGITACAO"],
                        errors="coerce"
                    )

                    df_temp = df_temp[df_temp["DT_EMISSAO"].notna()]

                    if df_temp.empty:
                        continue

                    # ID Único
                    df_temp["ID_UNICO"] = (
                        df_temp["EMPRESA / FILIAL"] + "|" + df_temp["PRODUTO"]
                    )

                    lista_mov.append(
                        df_temp[["ID_UNICO", "DT_EMISSAO"]]
                    )

        # =====================================================
        # CONSOLIDA ÚLTIMO MOVIMENTO
        # =====================================================

        if lista_mov:
            df_mov = pd.concat(lista_mov, ignore_index=True)

            df_mov_cons = (
                df_mov.groupby("ID_UNICO", as_index=False)
                .agg(Ult_Mov=("DT_EMISSAO", "max"))
            )
        else:
            df_mov_cons = pd.DataFrame(columns=["ID_UNICO", "Ult_Mov"])

    fim = time.time()

    print(f"Tempo total: {round(fim - inicio, 2)} segundos")
    print(f"Total registros consolidados: {len(df_mov_cons)}")

    buffer = io.BytesIO()
    df_mov_cons.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_mov_cons, buffer.getvalue()
