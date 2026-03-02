import pandas as pd
import zipfile
import io
import os

def executar_motor(uploaded_file):

    # ===============================
    # EXTRAÇÃO DO ZIP
    # ===============================
    zip_bytes = io.BytesIO(uploaded_file.read())

    with zipfile.ZipFile(zip_bytes, 'r') as z:
        lista_arquivos = z.namelist()

        # ===============================
        # ESTOQUE ATUAL (aba Detalhado)
        # ===============================
        arquivo_estoque = [f for f in lista_arquivos if "02_Estoque_Atual" in f and f.endswith(".xlsx")][0]

        with z.open(arquivo_estoque) as f:
            df_estoque = pd.read_excel(f, sheet_name="Detalhado", dtype=str)

        df_estoque.columns = df_estoque.columns.str.strip()

        colunas_necessarias = [
            "Data Fechamento",
            "Empresa",
            "Filial",
            "Código",
            "Quantidade",
            "Valor Total"
        ]

        for col in colunas_necessarias:
            if col not in df_estoque.columns:
                raise Exception(f"Coluna {col} não encontrada no estoque")

        # ===============================
        # TRATAMENTO BÁSICO
        # ===============================
        df_estoque["Código"] = df_estoque["Código"].astype(str).str.zfill(6)

        df_estoque["Quantidade"] = (
            df_estoque["Quantidade"]
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        ).astype(float)

        df_estoque["Valor Total"] = (
            df_estoque["Valor Total"]
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        ).astype(float)

        # Cria Mesclado
        df_estoque["Mesclado"] = df_estoque["Empresa"] + " " + df_estoque["Filial"]

        # ===============================
        # MATRIZ DE EMPRESAS
        # ===============================
        arquivo_matriz = [f for f in lista_arquivos if "05_Empresas" in f and f.endswith(".xlsx")][0]

        with z.open(arquivo_matriz) as f:
            df_matriz = pd.read_excel(f, dtype=str)

        df_matriz.columns = df_matriz.columns.str.strip()

        if "Mesclado" not in df_matriz.columns or "Empresa / Filial" not in df_matriz.columns:
            raise Exception("Colunas esperadas não encontradas na matriz de empresas")

        # ===============================
        # MERGE COM MATRIZ
        # ===============================
        df_final = df_estoque.merge(
            df_matriz[["Mesclado", "Empresa / Filial"]],
            on="Mesclado",
            how="left"
        )

        df_final["Empresa / Filial"] = df_final["Empresa / Filial"].fillna("N/D")

        # ===============================
        # ID ÚNICO
        # ===============================
        df_final["ID_UNICO"] = (
            df_final["Empresa / Filial"] + "|" + df_final["Código"]
        )

        # ===============================
        # SELEÇÃO FINAL
        # ===============================
        df_final = df_final[[
            "Data Fechamento",
            "Empresa / Filial",
            "Código",
            "Quantidade",
            "Valor Total",
            "ID_UNICO"
        ]]

        # ===============================
        # EXPORTAÇÃO PARA EXCEL
        # ===============================
        buffer = io.BytesIO()
        df_final.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_final, buffer.getvalue()
