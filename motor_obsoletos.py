import pandas as pd
import zipfile
import io
import time


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

    inicio = time.time()

    with zipfile.ZipFile(uploaded_file) as z:

        lista_mov = []

        arquivos_excel = [
            n for n in z.namelist()
            if "01_Entradas_Saidas" in n and n.endswith(".xlsx")
        ]

        print(f"Arquivos encontrados: {len(arquivos_excel)}")

        for arq in arquivos_excel:

            empresa_arquivo = arq.split("_")[1]
            empresa_normalizada = normalizar_empresa(empresa_arquivo)

            print(f"Lendo arquivo: {arq}")

            with z.open(arq) as f:
                xls = pd.ExcelFile(f, engine="openpyxl")

                for aba in ["ENTRADA", "SAIDA"]:

                    if aba not in xls.sheet_names:
                        continue

                    print(f"  Aba: {aba}")

                    df_temp = pd.read_excel(
                        xls,
                        sheet_name=aba,
                        engine="openpyxl"
                    )

                    df_temp.columns = df_temp.columns.str.strip()

                    if "ESTOQUE" not in df_temp.columns:
                        continue

                    df_temp = df_temp[df_temp["ESTOQUE"] == "S"]

                    if df_temp.empty:
                        continue

                    df_temp["Produto"] = (
                        df_temp["PRODUTO"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                    )

                    df_temp["DT Emissao"] = pd.to_datetime(
                        df_temp["DIGITACAO"],
                        errors="coerce"
                    )

                    df_temp = df_temp[df_temp["DT Emissao"].notna()]

                    df_temp["Filial"] = df_temp["FILIAL"].astype(str).str.title()

                    df_temp["Empresa / Filial"] = (
                        empresa_normalizada + " / " + df_temp["Filial"]
                    )

                    df_temp["ID_UNICO"] = (
                        df_temp["Empresa / Filial"] + "|" + df_temp["Produto"]
                    )

                    lista_mov.append(df_temp[["ID_UNICO", "DT Emissao"]])

        if lista_mov:
            df_mov = pd.concat(lista_mov)
            df_mov_cons = df_mov.groupby("ID_UNICO", as_index=False).agg(
                Ult_Mov=("DT Emissao", "max")
            )
        else:
            df_mov_cons = pd.DataFrame(columns=["ID_UNICO", "Ult_Mov"])

    fim = time.time()

    print(f"Tempo total: {round(fim - inicio, 2)} segundos")

    buffer = io.BytesIO()
    df_mov_cons.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_mov_cons, buffer.getvalue()
