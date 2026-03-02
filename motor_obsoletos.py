import os
import io
import zipfile
import pandas as pd


def executar_motor(uploaded_file):

    # ================================
    # EXTRAÇÃO DO ZIP
    # ================================
    pasta_base = "temp_extracao"

    if os.path.exists(pasta_base):
        import shutil
        shutil.rmtree(pasta_base)

    os.makedirs(pasta_base)

    with zipfile.ZipFile(uploaded_file) as z:
        z.extractall(pasta_base)

    # ================================
    # LOCALIZA PASTA 02_ESTOQUE_ATUAL
    # ================================
    pasta_estoque = os.path.join(pasta_base, "02_Estoque_Atual")

    if not os.path.exists(pasta_estoque):
        raise Exception("Pasta 02_Estoque_Atual não encontrada no ZIP")

    arquivos_excel = [
        f for f in os.listdir(pasta_estoque)
        if f.endswith(".xlsx")
    ]

    if not arquivos_excel:
        raise Exception("Nenhum arquivo .xlsx encontrado em 02_Estoque_Atual")

    caminho_arquivo = os.path.join(pasta_estoque, arquivos_excel[0])

    # ================================
    # LEITURA DO ESTOQUE
    # ================================
    df = pd.read_excel(caminho_arquivo, dtype=str)

    df.columns = df.columns.str.strip()

    # Mapeamento tolerante de nomes
    mapa_colunas = {
        "Código": "Produto",
        "Descricao": "Descricao",
        "Descrição": "Descricao",
        "Quantidade": "Saldo Atual",
        "Saldo Atual": "Saldo Atual",
        "Valor Total": "Custo Total",
        "Custo Total": "Custo Total",
        "Empresa / Filial": "Empresa / Filial",
        "Data Fechamento": "Data Fechamento"
    }

    for col_original, col_nova in mapa_colunas.items():
        if col_original in df.columns:
            df.rename(columns={col_original: col_nova}, inplace=True)

    colunas_necessarias = [
        "Empresa / Filial",
        "Produto",
        "Saldo Atual",
        "Custo Total"
    ]

    for col in colunas_necessarias:
        if col not in df.columns:
            raise Exception(f"Coluna {col} não encontrada no estoque")

    df_final = df[colunas_necessarias].copy()

    # ================================
    # EXPORTAÇÃO PARA EXCEL
    # ================================
    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
