import pandas as pd
import zipfile
import io


EMPRESAS_FILIAL_CONSIDERADAS = {
    "Robotica / Matriz",
    "Robotica / Filial Jaragua"
}


def normalizar_empresa(nome):
    nome = str(nome).upper()
    if "ROBOTICA" in nome:
        return "Robotica"
    if "TOOLS" in nome:
        return "Tools"
    if "MAQUINAS" in nome:
        return "Maquinas"
    if "ALLSERVICE" in nome:
        return "Service"
    return nome


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        lista_mov = []

        arquivos_csv = [
            n for n in z.namelist()
            if "04_Movimento" in n and n.endswith(".csv")
        ]

        for arq in arquivos_csv:

            # 🔎 Só testa arquivos que tenham Robotica no nome
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

            if "Quantidade" not in df_temp.columns or "DT Emissao" not in df_temp.columns:
                continue

            df_temp["Quantidade"] = pd.to_numeric(
                df_temp["Quantidade"], errors="coerce"
            )

            df_temp["DT Emissao"] = pd.to_datetime(
                df_temp["DT Emissao"],
                dayfirst=True,
                errors="coerce"
            )

            df_temp = df_temp[
                (df_temp["Quantidade"] != 0) &
                (df_temp["DT Emissao"].notna())
            ]

            if df_temp.empty:
                continue

            try:
                empresa_arquivo = arq.split("_")[1]
            except:
                continue

            empresa_normalizada = normalizar_empresa(empresa_arquivo)

            df_temp["Filial"] = df_temp["Filial"].astype(str).str.title()

            df_temp["Empresa / Filial"] = (
                empresa_normalizada + " / " + df_temp["Filial"]
            )

            df_temp = df_temp[
                df_temp["Empresa / Filial"]
                .isin(EMPRESAS_FILIAL_CONSIDERADAS)
            ]

            if df_temp.empty:
                continue

            df_temp["Produto"] = (
                df_temp["Produto"]
                .astype(str)
                .str.strip()
                .str.replace(".0", "", regex=False)
            )

            df_temp["ID_UNICO"] = (
                df_temp["Empresa / Filial"] + "|" + df_temp["Produto"]
            )

            lista_mov.append(
                df_temp[[
                    "Empresa / Filial",
                    "Produto",
                    "ID_UNICO",
                    "DT Emissao"
                ]]
            )

        if lista_mov:
            df_mov_robotica = pd.concat(lista_mov, ignore_index=True)
        else:
            df_mov_robotica = pd.DataFrame()

        buffer = io.BytesIO()
        df_mov_robotica.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_mov_robotica, buffer.getvalue()
