import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        lista_robotica = []

        arquivos_csv = [
            n for n in z.namelist()
            if "04_Movimento" in n and n.endswith(".csv")
        ]

        for arq in arquivos_csv:

            # 🔎 apenas arquivos que tenham ROBOTICA no nome
            if "ROBOTICA" not in arq.upper():
                continue

            with z.open(arq) as f:
                df_temp = pd.read_csv(
                    f,
                    sep=",",
                    encoding="cp1252",
                    skiprows=2,
                    dtype=str
                )

            df_temp.columns = df_temp.columns.str.strip()

            # Garantia mínima
            if "Quantidade" not in df_temp.columns:
                continue

            if "DT Emissao" not in df_temp.columns:
                continue

            df_temp["Quantidade"] = pd.to_numeric(
                df_temp["Quantidade"], errors="coerce"
            )

            df_temp["DT Emissao"] = pd.to_datetime(
                df_temp["DT Emissao"],
                dayfirst=True,
                errors="coerce"
            )

            # Apenas movimentos válidos
            df_temp = df_temp[
                (df_temp["Quantidade"] != 0) &
                (df_temp["DT Emissao"].notna())
            ]

            if df_temp.empty:
                continue

            # Normaliza produto
            df_temp["Produto"] = (
                df_temp["Produto"]
                .astype(str)
                .str.strip()
                .str.replace(".0", "", regex=False)
            )

            df_temp["Arquivo_Origem"] = arq

            lista_robotica.append(
                df_temp[[
                    "Filial",
                    "Produto",
                    "Quantidade",
                    "DT Emissao",
                    "Arquivo_Origem"
                ]]
            )

        if lista_robotica:
            df_resultado = pd.concat(lista_robotica, ignore_index=True)
        else:
            df_resultado = pd.DataFrame()

        buffer = io.BytesIO()
        df_resultado.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_resultado, buffer.getvalue()
