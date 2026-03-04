import pandas as pd
import os

CAMINHO_BASE = "data/base_historica.parquet"


def atualizar_base_historica(df_final):

    colunas = [
        "Data Fechamento",
        "Empresa / Filial",
        "Conta",
        "Produto",
        "Descricao",
        "Saldo Atual",
        "Vlr Unit",
        "Custo Total",
        "Meses Ult Mov",
        "Status Estoque",
        "Status do Movimento"
    ]

    df_snapshot = df_final[colunas].copy()

    df_snapshot["Data Fechamento"] = pd.to_datetime(df_snapshot["Data Fechamento"])

    data_ref = df_snapshot["Data Fechamento"].iloc[0]

    if os.path.exists(CAMINHO_BASE):

        df_hist = pd.read_parquet(CAMINHO_BASE)

        df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"])

        df_hist = df_hist[df_hist["Data Fechamento"] != data_ref]

        df_hist = pd.concat(
            [df_hist, df_snapshot],
            ignore_index=True
        )

    else:

        df_hist = df_snapshot

    df_hist = df_hist.sort_values(
        ["Data Fechamento", "Empresa / Filial", "Produto"]
    )

    df_hist.to_parquet(
        CAMINHO_BASE,
        index=False
    )

    return df_hist
