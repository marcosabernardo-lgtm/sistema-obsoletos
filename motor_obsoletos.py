import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        caminho_robotica = "04_Movimento/05_Robotica.csv"

        if caminho_robotica not in z.namelist():
            return pd.DataFrame({"Erro": ["Arquivo Robotica não encontrado"]}), None

        with z.open(caminho_robotica) as f:
            df = pd.read_csv(
                f,
                sep=",",
                encoding="cp1252",
                skiprows=2,
                dtype=str
            )

        df.columns = df.columns.str.strip()

        # Mostrar primeiras 20 linhas com colunas principais
        colunas_interesse = [c for c in df.columns if c in [
            "Filial",
            "Produto",
            "Quantidade",
            "DT Emissao"
        ]]

        df_resultado = df[colunas_interesse].head(50)

        buffer = io.BytesIO()
        df_resultado.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_resultado, buffer.getvalue()
