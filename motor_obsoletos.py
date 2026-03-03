import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        caminho_robotica = "04_Movimento/05_Robotica.csv"

        with z.open(caminho_robotica) as f:
            conteudo = f.read().decode("cp1252")

        # 🔥 remove duas primeiras linhas (SD3 + linha vazia)
        linhas = conteudo.splitlines()[2:]

        # 🔥 remove aspas e vírgula final
        linhas_tratadas = []
        for linha in linhas:
            linha = linha.rstrip(",")       # remove vírgula final
            linha = linha.replace('"', "")  # remove aspas
            linhas_tratadas.append(linha)

        texto_limpo = "\n".join(linhas_tratadas)

        # 🔥 agora sim converte corretamente
        df = pd.read_csv(
            io.StringIO(texto_limpo),
            sep=",",
            dtype=str
        )

        df.columns = df.columns.str.strip()

        df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce")

        df["DT Emissao"] = pd.to_datetime(
            df["DT Emissao"],
            dayfirst=True,
            errors="coerce"
        )

        df = df[
            (df["Quantidade"] != 0) &
            (df["DT Emissao"].notna())
        ]

        df["Produto"] = df["Produto"].astype(str).str.strip()

        df_resultado = df[[
            "Filial",
            "Produto",
            "Quantidade",
            "DT Emissao"
        ]].sort_values(by="DT Emissao", ascending=False)

        buffer = io.BytesIO()
        df_resultado.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_resultado, buffer.getvalue()
