import pandas as pd
import zipfile
import io

def ler_movimentacoes(caminho_zip):

    lista_dfs = []

    with zipfile.ZipFile(caminho_zip, 'r') as z:

        # Lista todos CSVs dentro da pasta 04_Movimento
        arquivos_mov = [
            f for f in z.namelist()
            if "04_Movimento/" in f and f.lower().endswith(".csv")
        ]

        if not arquivos_mov:
            raise FileNotFoundError("Nenhum CSV encontrado na pasta 04_Movimento.")

        for nome_arquivo in arquivos_mov:

            with z.open(nome_arquivo) as arquivo:
                df = pd.read_csv(
                    io.TextIOWrapper(arquivo, encoding="cp1252"),
                    sep=",",
                    skiprows=2,
                    dtype=str,
                    engine="python"
                )

            # Remove coluna vazia (vírgula final gera isso)
            df = df.dropna(axis=1, how="all")

            # Guarda nome do arquivo
            df["ARQUIVO_ORIGEM"] = nome_arquivo.split("/")[-1]

            lista_dfs.append(df)

    # Junta tudo
    df_mov = pd.concat(lista_dfs, ignore_index=True)

    # 🔎 FILTRO FINAL → somente Robotica
    df_mov = df_mov[df_mov["ARQUIVO_ORIGEM"].str.contains("Robotica", case=False)]

    return df_mov
