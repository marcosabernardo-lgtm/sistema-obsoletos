import pandas as pd
import numpy as np


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


def score_risco(df_hist):
    """
    Calcula o Score de Risco de Obsolescência por item (0 a 100).

    Componentes:
      - 40 pts: Dias sem movimento (quanto mais parado, maior o risco)
      - 30 pts: Valor em risco (custo total do item)
      - 30 pts: Estagnação entre fechamentos (Ult_Movimentacao igual em todos os fechamentos)

    Classificação final:
      - 0  a 30  → Baixo
      - 31 a 55  → Médio
      - 56 a 75  → Alto
      - 76 a 100 → Crítico
    """

    datas = sorted(df_hist["Data Fechamento"].unique())
    ultima = datas[-1]

    # Base: último fechamento, excluindo Em Fabricacao
    df_base = df_hist[df_hist["Data Fechamento"] == ultima].copy()
    df_base = df_base[
        df_base["Tipo de Estoque"].astype(str).str.strip().str.upper() != "EM FABRICACAO"
    ].copy()

    # ----------------------------------------------------------
    # COMPONENTE 1 — Dias sem movimento (0 a 40 pts)
    # ----------------------------------------------------------
    dias = df_base["Dias Sem Mov"].replace(9999, np.nan)
    p95 = dias.quantile(0.95)
    p95 = p95 if pd.notna(p95) and p95 > 0 else 1

    df_base["_score_dias"] = (
        dias.fillna(p95).clip(upper=p95) / p95 * 40
    )

    # ----------------------------------------------------------
    # COMPONENTE 2 — Valor em risco (0 a 30 pts)
    # ----------------------------------------------------------
    custo = df_base["Custo Total"].fillna(0).clip(lower=0)
    p95c = custo.quantile(0.95)
    p95c = p95c if pd.notna(p95c) and p95c > 0 else 1

    df_base["_score_custo"] = (
        custo.clip(upper=p95c) / p95c * 30
    )

    # ----------------------------------------------------------
    # COMPONENTE 3 — Estagnação entre fechamentos (0 a 30 pts)
    # Verifica se a Ult_Movimentacao não mudou em nenhum fechamento anterior
    # ----------------------------------------------------------
    df_base["_score_estag"] = 0.0

    if len(datas) >= 2:
        df_ant = df_hist[df_hist["Data Fechamento"] < ultima][
            ["Produto", "Empresa / Filial", "Data Fechamento", "Ult_Movimentacao"]
        ].copy()

        df_merge = df_base[["Produto", "Empresa / Filial", "Ult_Movimentacao"]].merge(
            df_ant,
            on=["Produto", "Empresa / Filial"],
            suffixes=("_atual", "_ant")
        )

        df_merge["_igual"] = (
            df_merge["Ult_Movimentacao_atual"] == df_merge["Ult_Movimentacao_ant"]
        )

        # Percentual de fechamentos anteriores com mesma data de movimento
        estag = (
            df_merge.groupby(["Produto", "Empresa / Filial"])["_igual"]
            .mean()
            .reset_index()
            .rename(columns={"_igual": "_perc_estag"})
        )

        df_base = df_base.merge(estag, on=["Produto", "Empresa / Filial"], how="left")
        df_base["_perc_estag"] = df_base["_perc_estag"].fillna(0)
        df_base["_score_estag"] = df_base["_perc_estag"] * 30

    # ----------------------------------------------------------
    # SCORE FINAL
    # ----------------------------------------------------------
    df_base["Score"] = (
        df_base["_score_dias"] +
        df_base["_score_custo"] +
        df_base["_score_estag"]
    ).clip(0, 100).round(1)

    # Classificação
    def classificar(score):
        if score <= 30:
            return "🟢 Baixo"
        elif score <= 55:
            return "🟡 Médio"
        elif score <= 75:
            return "🟠 Alto"
        return "🔴 Crítico"

    df_base["Risco"] = df_base["Score"].apply(classificar)

    # Colunas relevantes para exibição
    colunas = [
        "Empresa / Filial",
        "Produto",
        "Descricao",
        "Conta",
        "Tipo de Estoque",
        "Saldo Atual",
        "Custo Total",
        "Ult_Movimentacao",
        "Dias Sem Mov",
        "Meses Ult Mov",
        "Status do Movimento",
        "Score",
        "Risco",
    ]

    colunas_existentes = [c for c in colunas if c in df_base.columns]

    return (
        df_base[colunas_existentes]
        .sort_values("Score", ascending=False)
        .reset_index(drop=True)
    )
