import pandas as pd
import os

# Caminho absoluto baseado na localização do próprio arquivo
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO = os.path.join(BASE_DIR, "data", "estoque", "estoque_historico.parquet")


def salvar_fechamento_estoque(df_novo):

    # garantir datetime
    df_novo["Data Fechamento"] = pd.to_datetime(df_novo["Data Fechamento"])

    data_ref = df_novo["Data Fechamento"].iloc[0]

    # -------------------------------------------------
    # SE JÁ EXISTE BASE HISTÓRICA
    # -------------------------------------------------

    if os.path.exists(CAMINHO):

        df_hist = pd.read_parquet(CAMINHO)

        df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"])

        # remover mês que será substituído
        df_hist = df_hist[df_hist["Data Fechamento"] != data_ref]

        # concatenar novo fechamento
        df_final = pd.concat([df_hist, df_novo], ignore_index=True)

    else:

        df_final = df_novo.copy()

    # ordenar histórico
    df_final = df_final.sort_values("Data Fechamento")

    # salvar
    df_final.to_parquet(CAMINHO, index=False)

    return CAMINHO