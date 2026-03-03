def executar_entradas_saidas(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        arquivos_excel = [
            f for f in z.namelist()
            if "01_Entradas_Saidas/" in f and f.lower().endswith(".xlsx")
        ]

        if not arquivos_excel:
            raise Exception("Nenhum arquivo encontrado em 01_Entradas_Saidas")

        lista = []

        for nome_arquivo in arquivos_excel:

            with z.open(nome_arquivo) as arq:

                xl = pd.ExcelFile(arq)

                empresa = nome_arquivo.split("/")[-1].split("_")[1]

                for aba, tipo in [("ENTRADA", "Entrada"), ("SAIDA", "Saida")]:

                    if aba in xl.sheet_names:

                        df = pd.read_excel(
                            arq,
                            sheet_name=aba,
                            dtype=str,
                            engine="openpyxl"
                        )

                        df = df[[
                            "FILIAL",
                            "PRODUTO",
                            "DIGITACAO",
                            "ESTOQUE",
                            "QUANTIDADE"
                        ]].copy()

                        df["Tipo Movimento"] = tipo
                        df["Empresa"] = empresa

                        lista.append(df)

        df_final = pd.concat(lista, ignore_index=True)

        return df_final
