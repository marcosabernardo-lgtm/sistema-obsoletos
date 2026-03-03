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

        arquivo_estoque = next(
            (n for n in z.namelist()
             if "02_Estoque_Atual" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_estoque:
            raise Exception("Arquivo 02_Estoque_Atual não encontrado no ZIP")

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

        # Normaliza Empresa e Filial apenas para montar Empresa / Filial
        df_estoque["Empresa"] = df_estoque["Empresa"].apply(normalizar_empresa)
        df_estoque["Filial"] = df_estoque["Filial"].astype(str).str.title()

        df_estoque["Empresa / Filial"] = (
            df_estoque["Empresa"] + " / " + df_estoque["Filial"]
        )

        # Produto preservando zeros
        df_estoque["Produto"] = (
            df_estoque["Produto"]
            .astype(str)
            .str.strip()
            .str.replace(".0", "", regex=False)
        )

        df_estoque["ID_UNICO"] = (
            df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]
        )

        df_estoque["Saldo Atual"] = pd.to_numeric(
            df_estoque["Saldo Atual"], errors="coerce"
        )

        df_estoque["Custo Total"] = pd.to_numeric(
            df_estoque["Custo Total"], errors="coerce"
        )

        # 🔥 REMOVE Empresa e Filial
        df_estoque = df_estoque.drop(columns=["Empresa", "Filial"])

        # Organiza colunas
        colunas = df_estoque.columns.tolist()
        nova_ordem = ["Data Fechamento", "Empresa / Filial"]
        demais = [c for c in colunas if c not in nova_ordem]

        df_final = df_estoque[nova_ordem + demais]

        buffer = io.BytesIO()
        df_final.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_final, buffer.getvalue()
