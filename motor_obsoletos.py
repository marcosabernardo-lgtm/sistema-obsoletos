import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        caminho_robotica = "04_Movimento/05_Robotica.csv"

        with z.open(caminho_robotica) as f:
            df = pd.read_csv(
                f,
                sep=",",
                encoding="cp1252",
                skiprows=2,
                dtype=str
            )

        # Mostrar nomes exatos das colunas
        df_colunas = pd.DataFrame({
            "Colunas_Reais": df.columns.tolist()
        })

        buffer = io.BytesIO()
        df_colunas.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_colunas, buffer.getvalue()
