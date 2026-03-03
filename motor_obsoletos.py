        # =====================================================
        # MERGE FINAL (se houver movimentação)
        # =====================================================

        if lista_mov:
            df_mov = pd.concat(lista_mov, ignore_index=True)

            df_mov_cons = (
                df_mov.groupby("ID_UNICO", as_index=False)
                .agg(Ult_Mov=("DT Emissao", "max"))
            )
        else:
            df_mov_cons = pd.DataFrame(columns=["ID_UNICO", "Ult_Mov"])

        df_final = df_estoque.merge(
            df_mov_cons,
            on="ID_UNICO",
            how="left"
        )

        # =====================================================
        # FILTRO APENAS ROBOTICA
        # =====================================================

        df_robotica = df_final[
            df_final["Empresa / Filial"].str.contains("Robotica", na=False)
        ][[
            "Empresa / Filial",
            "Produto",
            "Saldo Atual",
            "Custo Total",
            "ID_UNICO",
            "Ult_Mov"
        ]]

        buffer = io.BytesIO()
        df_robotica.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_robotica, buffer.getvalue()
