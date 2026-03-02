import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    # ================================
    # LEITURA DO ZIP
    # ================================
    with zipfile.ZipFile(uploaded_file) as z:

        # Procurar arquivo de estoque atual
        arquivo_estoque = [f for f in z.namelist() if "02_Estoque_Atual" in f and f.endswith(".xlsx")]

        if not arquivo_estoque:
            raise Exception("Arquivo de Estoque Atual não encontrado no ZIP")

        with z.open(arquivo_estoque[0]) as f:
            df_estoque = pd.read_excel(f, sheet_name="Detalhado")

    # ================================
    # LIMPEZA DE COLUNAS
    # ================================
    df_estoque.columns = df_estoque.columns.str.strip()

    print("Colunas encontradas no estoque:")
    print(df_estoque.columns.tolist())

    # ================================
    # VALIDAÇÃO DE COLUNAS OBRIGATÓRIAS
    # ================================
    colunas_obrigatorias = [
        "Data Fechamento",
        "Empresa",
        "Filial",
        "Código",
        "Quantidade",
        "Valor Total"
    ]

    for col in colunas_obrigatorias:
        if col not in df_estoque.columns:
            raise Exception(f"Coluna {col} não encontrada no estoque")

    # ================================
    # BASE FINAL (por enquanto só estoque)
    # ================================
    df_final = df_estoque.copy()

    # ================================
    # EXPORTAÇÃO EXCEL
    # ================================
    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
