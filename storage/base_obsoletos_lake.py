import pandas as pd
import os

PASTA = "data/obsoletos"


def salvar_fechamento_obsoletos(df):

    os.makedirs(PASTA, exist_ok=True)

    data_ref = pd.to_datetime(df["Data Fechamento"].iloc[0])

    nome = data_ref.strftime("%Y_%m")

    caminho = f"{PASTA}/{nome}.parquet"

    df.to_parquet(caminho, index=False)

    return caminho