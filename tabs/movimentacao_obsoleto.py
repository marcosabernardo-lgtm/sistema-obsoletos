def render(df_kpi, moeda_br):

    df = df_kpi.copy()

    datas = sorted(df["Data Fechamento"].unique())

    data_atual = datas[-1]
    data_anterior = datas[-2]

    df_atual = df[df["Data Fechamento"] == data_atual].copy()
    df_ant = df[df["Data Fechamento"] == data_anterior].copy()

    df_atual["obsoleto"] = df_atual["Status do Movimento"] != "Até 6 meses"
    df_ant["obsoleto"] = df_ant["Status do Movimento"] != "Até 6 meses"

    chave = ["Empresa / Filial", "Produto"]

    base = df_atual.merge(
        df_ant[chave + ["obsoleto"]],
        on=chave,
        how="left",
        suffixes=("_atual", "_ant")
    )

    base["obsoleto_ant"] = base["obsoleto_ant"].fillna(False)

    entrou = base[
        (base["obsoleto_atual"] == True)
        &
        (base["obsoleto_ant"] == False)
    ].copy()

    saiu = base[
        (base["obsoleto_atual"] == False)
        &
        (base["obsoleto_ant"] == True)
    ].copy()

    # AQUI começam os cálculos dos cards
