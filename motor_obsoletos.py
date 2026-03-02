import zipfile
import pandas as pd
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # ============================
        # LOCALIZA PASTA DO ESTOQUE
        # ============================
        arquivos_estoque = [
            f for f in z.namelist()
            if "02_Estoque_Atual" in f and f.endswith(".xlsx")
        ]

        if not arquivos_estoque:
            raise Exception("Nenhum arquivo encontrado em 02_Estoque_Atual")

        arquivo_estoque = arquivos_estoque[0]

        with z.open(arquivo_estoque) as file:
            df_estoque = pd.read_excel(file, dtype=str)

    # Remove espaços extras nos nomes das colunas
    df_estoque.columns = df_estoque.columns.str.strip()

    # ============================
    # EXPORTAÇÃO PARA EXCEL
    # ============================
    buffer = io.BytesIO()
    df_estoque.to_excel(buffer, index=False)
    buffer.seek(0)

    print("Colunas encontradas no estoque:")
    print(df_estoque.columns.tolist())

    return df_estoque, buffer.getvalue()
