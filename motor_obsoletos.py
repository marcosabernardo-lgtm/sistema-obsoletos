import pandas as pd
import zipfile

def testar_entradas_saidas(caminho_zip):

    with zipfile.ZipFile(caminho_zip) as z:

        # Carrega matriz Empresa / Filial
        arquivo_matriz = next(
            n for n in z.namelist()
            if "05_Empresas" in n and n.endswith(".xlsx")
        )
        with z.open(arquivo_matriz) as f:
            df_matriz = pd.read_excel(f, dtype=str, engine="openpyxl")

        print("=== 05_Empresas ===")
        print(df_matriz)
        print()

        lista_exc = []

        arquivos_exc = [
            n for n in z.namelist()
            if "01_Entradas_Saidas" in n and n.endswith(".xlsx")
        ]

        for arq in arquivos_exc:

            # Extrai nome da empresa do arquivo: "01_Tools.xlsx" → "Tools"
            nome_arquivo = arq.split("/")[-1]           # "01_Tools.xlsx"
            empresa = nome_arquivo.split("_")[1]        # "Tools"
            empresa = empresa.replace(".xlsx", "")      # segurança

            print(f">>> Processando: {nome_arquivo} | Empresa: {empresa}")

            with z.open(arq) as f:
                xl = pd.ExcelFile(f, engine="openpyxl")

            print(f"    Abas encontradas: {xl.sheet_names}")

            for aba, tipo in [("ENTRADA", "Entrada"), ("SAIDA", "Saida")]:

                if aba not in xl.sheet_names:
                    print(f"    ⚠️  Aba '{aba}' não encontrada")
                    continue

                with z.open(arq) as f:
                    df = pd.read_excel(
                        f, sheet_name=aba,
                        dtype=str, engine="openpyxl"
                    )

                df.columns = [str(c).upper().strip() for c in df.columns]

                print(f"    Colunas ({aba}): {list(df.columns)}")

                colunas_necessarias = {"FILIAL", "PRODUTO", "DIGITACAO", "ESTOQUE", "QUANTIDADE"}
                if not colunas_necessarias.issubset(df.columns):
                    print(f"    ❌ Colunas faltando: {colunas_necessarias - set(df.columns)}")
                    continue

                df = df[["FILIAL", "PRODUTO", "DIGITACAO", "ESTOQUE", "QUANTIDADE"]].copy()
                df["Tipo Movimento"] = tipo

                # Trata número brasileiro
                df["QUANTIDADE"] = (
                    df["QUANTIDADE"]
                    .astype(str)
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False)
                )
                df["QUANTIDADE"] = pd.to_numeric(df["QUANTIDADE"], errors="coerce")
                df["DIGITACAO"]  = pd.to_datetime(df["DIGITACAO"], errors="coerce")

                df = df[(df["ESTOQUE"] == "S") & (df["QUANTIDADE"] != 0) & df["DIGITACAO"].notna()]

                if df.empty:
                    print(f"    ⚠️  Sem dados válidos em '{aba}'")
                    continue

                # Monta Mesclado: "Tools 00", "Tools 01" etc.
                df["FILIAL"]   = df["FILIAL"].astype(str).str.strip()
                df["Mesclado"] = empresa + " " + df["FILIAL"]

                # Resolve Empresa / Filial via matriz
                df = df.merge(
                    df_matriz[["Mesclado", "Empresa / Filial"]],
                    on="Mesclado", how="left"
                )

                nao_resolvidos = df["Empresa / Filial"].isna().sum()
                if nao_resolvidos:
                    print(f"    ⚠️  {nao_resolvidos} linhas com Empresa/Filial não resolvida")
                    print(f"    Mesclados únicos não resolvidos: {df[df['Empresa / Filial'].isna()]['Mesclado'].unique()}")

                df["Empresa / Filial"] = df["Empresa / Filial"].fillna("N/D")

                df["PRODUTO"] = df["PRODUTO"].astype(str).str.strip().str.upper()
                df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["PRODUTO"]

                df = df.rename(columns={
                    "PRODUTO":    "Produto",
                    "DIGITACAO":  "DT Emissao",
                    "QUANTIDADE": "Qtde"
                })

                resultado = df[["ID_UNICO", "Empresa / Filial", "Produto", "DT Emissao", "Tipo Movimento", "Qtde"]]
                lista_exc.append(resultado)

                print(f"    ✅ {aba}: {len(resultado)} registros válidos")

        if lista_exc:
            df_final = pd.concat(lista_exc, ignore_index=True)
            print(f"\n=== RESULTADO FINAL: {len(df_final)} registros ===")
            print(df_final.head(10))
            print(f"\nEmpresas/Filiais encontradas:")
            print(df_final["Empresa / Filial"].value_counts())
        else:
            print("❌ Nenhum dado encontrado")

        return lista_exc

