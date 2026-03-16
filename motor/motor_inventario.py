import pandas as pd
import zipfile
from pathlib import Path


CAMINHO_ZIP = "analytics/dados_inventario/2026-02-28.zip"
CAMINHO_ESTOQUE = "data/estoque/estoque_historico.parquet"
CAMINHO_SAIDA = "data/inventario/inventario_historico.parquet"


def extrair_info_nome(nome_arquivo):

    nome = Path(nome_arquivo).stem

    empresa = nome[:4]

    dia = int(nome[4:6])
    mes = int(nome[6:8])
    ano = int(nome[8:12])

    data = pd.Timestamp(ano, mes, dia)
    data_fechamento = data + pd.offsets.MonthEnd(0)

    return empresa, data_fechamento


def processar_zip():

    inventarios = []

    with zipfile.ZipFile(CAMINHO_ZIP) as z:

        arquivos = [
            f for f in z.namelist()
            if f.startswith("01_Inventario/") and f.endswith(".xlsx")
        ]

        for arquivo in arquivos:

            empresa, data_inventario = extrair_info_nome(arquivo.split("/")[-1])

            df = pd.read_excel(z.open(arquivo), header=1)

            df.columns = df.columns.str.strip().str.upper()

            df = df.rename(columns={
                "CODIGO": "Codigo",
                "DESCRICAO": "Descricao",
                "QUANTIDADE INVENTARIADA": "Qtd_Inventariada",
                "QTD NA DATA DO INVENTARIO": "Qtd_Protheus",
                "DIFERENCA QUANTIDADE": "Qtd_Divergente",
                "DIFERENCA VALOR": "Valor_Divergente"
            })

            df = df[df["Codigo"].notna()]

            df["Codigo"] = df["Codigo"].astype(str).str.strip()

            df["Empresa"] = empresa
            df["Data_Inventario"] = data_inventario

            df["Qtd_Itens_Inventariados"] = 1
            df["Qtd_Itens_Divergentes"] = (df["Qtd_Divergente"] != 0).astype(int)

            inventarios.append(df)

        inventario = pd.concat(inventarios, ignore_index=True)

        empresas = pd.read_excel(z.open("02_Empresas/02_Empresas.xlsx"))

        empresas = empresas.rename(columns={
            "Empresa": "Empresa",
            "Empresa / Filial": "Nome_Empresa"
        })

        inventario["Empresa"] = inventario["Empresa"].astype(str)
        empresas["Empresa"] = empresas["Empresa"].astype(str)

        inventario = inventario.merge(empresas, on="Empresa", how="left")

        estoque = pd.read_parquet(CAMINHO_ESTOQUE)

        estoque["Produto"] = estoque["Produto"].astype(str).str.strip()

        estoque["Valor_Unitario"] = estoque["Custo Total"] / estoque["Saldo Atual"]
        estoque["Valor_Unitario"] = estoque["Valor_Unitario"].fillna(0)

        estoque = estoque[[
            "Data Fechamento",
            "Produto",
            "Valor_Unitario"
        ]]

        inventario = inventario.merge(
            estoque,
            left_on=["Codigo", "Data_Inventario"],
            right_on=["Produto", "Data Fechamento"],
            how="left"
        )

        inventario["Valor_Protheus"] = (
            inventario["Qtd_Protheus"] * inventario["Valor_Unitario"]
        )

        inventario["Valor_Inventariado"] = (
            inventario["Qtd_Inventariada"] * inventario["Valor_Unitario"]
        )

        inventario = inventario[[
            "Nome_Empresa",
            "Empresa",
            "Data_Inventario",
            "Codigo",
            "Descricao",
            "Qtd_Inventariada",
            "Qtd_Protheus",
            "Qtd_Divergente",
            "Valor_Unitario",
            "Valor_Protheus",
            "Valor_Inventariado",
            "Valor_Divergente",
            "Qtd_Itens_Inventariados",
            "Qtd_Itens_Divergentes"
        ]]

        Path("data/inventario").mkdir(parents=True, exist_ok=True)

        inventario.to_parquet(CAMINHO_SAIDA, index=False)

        print("Inventario processado com sucesso")


if __name__ == "__main__":
    processar_zip()