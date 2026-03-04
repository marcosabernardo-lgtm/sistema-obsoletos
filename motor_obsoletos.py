# ==========================================================
    # BLOCO FINAL (APENAS ACRESCENTADO)
    # ==========================================================

    DataBase = pd.to_datetime(df_final["Data Fechamento"].iloc[0])

    df_final["Dias Sem Mov"] = (
        DataBase - df_final["Ult_Movimentacao"]
    ).dt.days.fillna(9999)

    df_final["Meses Ult Mov"] = np.where(
        df_final["Ult_Movimentacao"].notna(),
        (DataBase.year - df_final["Ult_Movimentacao"].dt.year) * 12 +
        (DataBase.month - df_final["Ult_Movimentacao"].dt.month),
        np.nan
    )

    df_final["Status Estoque"] = np.where(
        df_final["Tipo de Estoque"] == "EM FABRICACAO",
        "Até 6 meses",
        np.where(df_final["Dias Sem Mov"] > 180, "Obsoleto", "Até 6 meses")
    )

    def status_mov(row):
        if row["Tipo de Estoque"] == "EM FABRICACAO":
            return "Até 6 meses"
        if pd.isna(row["Meses Ult Mov"]):
            return "Sem Movimento"
        if row["Meses Ult Mov"] <= 6:
            return "Até 6 meses"
        if row["Meses Ult Mov"] <= 12:
            return "Até 1 ano"
        if row["Meses Ult Mov"] <= 24:
            return "Até 2 anos"
        return "+ 2 anos"

    df_final["Status do Movimento"] = df_final.apply(status_mov, axis=1)

    def formatar(row):
        if row["Tipo de Estoque"] == "EM FABRICACAO":
            return "Em fabricação"
        if pd.isna(row["Ult_Movimentacao"]):
            return "Sem movimento"

        dias = (DataBase - row["Ult_Movimentacao"]).days
        anos = dias // 365
        meses = (dias % 365) // 30
        dias_rest = (dias % 365) % 30

        return f"{anos} anos {meses} meses {dias_rest} dias"

    df_final["Ano Meses Dias"] = df_final.apply(formatar, axis=1)

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
