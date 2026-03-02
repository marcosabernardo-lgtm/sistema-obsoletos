import pandas as pd
import zipfile
import io
import os

def executar_motor(uploaded_file):

    # ================================
    # ABRIR ZIP
    # ================================
    with zipfile.ZipFile(uploaded_file) as z:

        # Procurar arquivo de estoque dentro do ZIP
        arquivo_estoque = None

        for nome in z.namelist():
            if "02_Estoque_Atual" in nome and nome.endswith(".xlsx"):
                arquivo_estoque = nome
                break

        if arquivo_estoque is None:
            raise Exception("Arquivo 02_Estoque_Atual não encontrado no ZIP")

        with z.open(arquivo_estoque) as f:
            df_estoque = pd.read_excel(f, sheet_name="Detalhado", dtype=str)

    # ================================
    # LIMPEZA BÁSICA
    # ================================
    df_estoque.columns = df_estoque.columns.str.strip()

    print("Colunas encontradas na aba Detalhado:")
    print(df_estoque.columns.tolist())

    # ================================
    # TRABALHAR APENAS ESTOQUE (TEMPORÁRIO)
    # ================================
    df_final = df_estoque.copy()

    # ================================
    # EXPORTAÇÃO PARA EXCEL
    # ================================
    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
