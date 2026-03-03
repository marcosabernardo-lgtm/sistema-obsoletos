import pandas as pd
import zipfile
import io

def ler_movimentacao_robotica(caminho_zip):
    with zipfile.ZipFile(caminho_zip, 'r') as z:
        
        # Localiza o arquivo 05_Robotica.csv dentro da pasta 04_Movimento
        nome_arquivo = next(
            (f for f in z.namelist() if "04_Movimento/05_Robotica.csv" in f),
            None
        )
        
        if nome_arquivo is None:
            raise FileNotFoundError("05_Robotica.csv não encontrado no ZIP.")

        # Lê o arquivo direto da memória
        with z.open(nome_arquivo) as arquivo:
            df = pd.read_csv(
                io.TextIOWrapper(arquivo, encoding="cp1252"),
                sep=",",
                skiprows=2,      # pula SD3 e linha vazia
                dtype=str,       # preserva zeros à esquerda
                engine="python"  # tolera vírgula final
            )

    # Remove colunas totalmente vazias (vírgula final gera isso)
    df = df.dropna(axis=1, how="all")

    return df
