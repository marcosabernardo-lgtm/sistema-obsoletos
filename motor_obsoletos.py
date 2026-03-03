import zipfile
import io
import pandas as pd

def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        arquivos_csv = [
            n for n in z.namelist()
            if "04_Movimento" in n and n.endswith(".csv")
        ]

        df_lista = pd.DataFrame({"Arquivos_encontrados": arquivos_csv})

        buffer = io.BytesIO()
        df_lista.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_lista, buffer.getvalue()
