import pandas as pd
import zipfile
import os
import shutil
from pathlib import Path
import io


def executar_motor(uploaded_file):

    pasta_base = "temp_upload"

    if os.path.exists(pasta_base):
        shutil.rmtree(pasta_base)

    os.makedirs(pasta_base)

    # Extrai o ZIP
    with zipfile.ZipFile(uploaded_file, 'r') as z:
        z.extractall(pasta_base)

    # Lista estrutura encontrada
    pastas_encontradas = os.listdir(pasta_base)

    pastas_esperadas = [
        "01_Entradas_Saidas",
        "02_Estoque_Atual",
        "04_Movimento",
        "05_Empresas",
        "06_Usadas"
    ]

    faltando = [p for p in pastas_esperadas if p not in pastas_encontradas]

    if faltando:
        raise Exception(f"Pastas faltando no ZIP: {faltando}")

    # Se chegou até aqui, estrutura está OK
    df_teste = pd.DataFrame({
        "Status": ["Estrutura validada com sucesso"]
    })

    # Criar Excel em memória corretamente
    buffer = io.BytesIO()
    df_teste.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_teste, buffer.getvalue()
