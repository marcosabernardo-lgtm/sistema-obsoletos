import pandas as pd
import zipfile
import io


def normalizar_empresa(nome):
    nome = str(nome).upper()
    if "TOOLS" in nome:
        return "Tools"
    if "MAQUINAS" in nome:
        return "Maquinas"
    if "ALLSERVICE" in nome:
        return "Service"
    if "ROBOTICA" in nome:
        return "Robotica"
    return nome


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # =====================================================
        # ESTOQUE
        # =====================================================

        arquivo_estoque = next(
            (n for n in z.namelist()
             if "02_Estoque_Atual" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_estoque:
            raise Exception("02_Estoque_Atual não encontrado")

        with z.open(arquivo_estoque) as f:
            df_estoque = pd.read_excel(
                f,
                sheet_name="Detalhado",
                dtype={"Código": str},
                engine="openpyxl"
            )

        df_estoque = df_estoque.rename(columns={
            "Valor Total": "Custo Total",
            "Código": "Produto",
            "Descrição": "Descricao",
            "Quantidade": "Saldo Atual"
        })

        df_estoque["Empresa"] = df_estoque["Empresa"].apply(normalizar_empresa)
        df_estoque["Filial"] = df_estoque["Filial"].astype(str).str.title()

        df_estoque["Empresa / Filial"] = (
            df_estoque["Empresa"] + " / " + df_estoque["Filial"]
        )

        # 🔹 Padronização segura do Produto
        df_estoque["Produto"] = (
            df_estoque["Produto"]
            .astype(str)
            .str.strip()
            .str.replace(".0", "", regex=False)
        )

        # 🔹 ID_UNICO
        df_estoque["ID_UNICO"] = (
            df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]
        )

        # 🔎 FILTRO APENAS ROBOTICA
        df_robotica = df_estoque[
            df_estoque["Empresa / Filial"].str.contains("Robotica", na=False)
        ][["Empresa / Filial", "Produto", "ID_UNICO"]]

        buffer = io.BytesIO()
        df_robotica.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_robotica, buffer.getvalue()
