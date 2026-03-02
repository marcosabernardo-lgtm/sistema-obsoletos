import os
import io
import zipfile
import uuid
import pandas as pd


def executar_motor(uploaded_file):

    # ===============================
    # CRIA PASTA TEMPORÁRIA ÚNICA
    # ===============================
    pasta_base = f"temp_upload_{uuid.uuid4().hex}"
    os.makedirs(pasta_base)

    # ===============================
    # EXTRAI ZIP
    # ===============================
    zip_bytes = uploaded_file.read()

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        z.extractall(pasta_base)

    # ===============================
    # ESTOQUE ATUAL
    # ===============================
    pasta_estoque = os.path.join(pasta_base, "02_Estoque_Atual")

    arquivos = [f for f in os.listdir(pasta_estoque) if f.endswith(".xlsx")]

    if not arquivos:
        raise Exception("Nenhum arquivo encontrado em 02_Estoque_Atual")

    caminho_estoque = os.path.join(pasta_estoque, arquivos[0])

    df_estoque = pd.read_excel(caminho_estoque)

    df_estoque.columns = df_estoque.columns.str.strip()

    colunas_necessarias = [
        "Empresa / Filial",
        "Produto",
        "Saldo Atual",
        "Custo Total"
    ]

    for col in colunas_necessarias:
        if col not in df_estoque.columns:
            raise Exception(f"Coluna {col} não encontrada no estoque")

    df_final = df_estoque[colunas_necessarias].copy()

    # ===============================
    # DATA BASE
    # ===============================
    if "Data Fechamento" in df_estoque.columns:
        df_final["Data_Base"] = df_estoque["Data Fechamento"]
    else:
        df_final["Data_Base"] = pd.Timestamp.today().normalize()

    # ===============================
    # HISTÓRICO AUTOMÁTICO
    # ===============================
    historico_path = "historico_obsoletos.csv"

    if os.path.exists(historico_path):
        df_historico_antigo = pd.read_csv(historico_path, dtype=str)
        df_historico = pd.concat(
            [df_historico_antigo, df_final.astype(str)],
            ignore_index=True
        )
    else:
        df_historico = df_final.astype(str)

    df_historico.to_csv(historico_path, index=False)

    # ===============================
    # EXPORTAÇÃO PARA EXCEL
    # ===============================
    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    print("Colunas encontradas no estoque:")
print(df_estoque.columns.tolist())

    return df_final, buffer.getvalue()
