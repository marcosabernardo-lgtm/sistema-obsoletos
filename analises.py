import pandas as pd


def evolucao_estoque(df_hist):

    total = (
        df_hist
        .groupby("Data Fechamento")["Custo Total"]
        .sum()
        .reset_index(name="Estoque Total")
    )

    obsoleto = (
        df_hist[df_hist["Status Estoque"] == "Obsoleto"]
        .groupby("Data Fechamento")["Custo Total"]
        .sum()
        .reset_index(name="Estoque Obsoleto")
    )

    df = total.merge(
        obsoleto,
        on="Data Fechamento",
        how="left"
    )

    df["Estoque Obsoleto"] = df["Estoque Obsoleto"].fillna(0)

    df["% Obsoleto"] = (
        df["Estoque Obsoleto"] /
        df["Estoque Total"]
    )

    return df.sort_values("Data Fechamento")
