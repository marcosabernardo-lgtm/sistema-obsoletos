import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        caminho_robotica = "04_Movimento/05_Robotica.csv"

        with z.open(caminho_robotica) as f:
            df = pd.read_csv(
                f,
                sep=",",          # ← CORRETO
                quotechar='"',    # ← IMPORTANTE
                encoding="cp1252",
                skiprows=2,       # ← CORRETO
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

        df["Produto"] = (
            df["Produto"]
            .astype(str)
            .str.strip()
            .str.replace(".0", "", regex=False)
        )

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
