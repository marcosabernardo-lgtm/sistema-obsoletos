import pandas as pd
import os

BASE_ESTOQUE = "data/base_estoque.parquet"


def atualizar_base_estoque(df_novo):

    os.makedirs("data", exist_ok=True)

    if os.path.exists(BASE_ESTOQUE):

        df_hist = pd.read_parquet(BASE_ESTOQUE)

        df_final = pd.concat([df_hist, df_novo], ignore_index=True)

    else:

        df_final = df_novo.copy()

    df_final.to_parquet(BASE_ESTOQUE, index=False)

    return df_final