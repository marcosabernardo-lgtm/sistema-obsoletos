import os
import pandas as pd
import zipfile
from pathlib import Path


PASTA_ZIP       = "analytics/dados_inventario"
CAMINHO_ESTOQUE = "data/estoque/estoque_historico.parquet"
CAMINHO_SAIDA   = "data/inventario/inventario_historico.parquet"


# ==========================================================
# EXTRAI EMPRESA E DATA DO NOME DO ARQUIVO
# ==========================================================

def extrair_info_nome(nome_arquivo):

    nome = Path(nome_arquivo).stem

    try:
        empresa       = nome[:4]
        dia           = int(nome[4:6])
        mes           = int(nome[6:8])
        ano           = int(nome[8:12])
        data          = pd.Timestamp(ano, mes, dia)
        data_fechamento = data + pd.offsets.MonthEnd(0)
    except Exception:
        raise ValueError(f"Nome de arquivo fora do padrão esperado: {nome_arquivo}")

    return empresa, data_fechamento


# ==========================================================
# PROCESSA TODOS OS ZIPs DA PASTA
# ==========================================================

def processar_zip():

    # ----------------------------------------------------------
    # BUSCA TODOS OS ZIPs DA PASTA
    # ----------------------------------------------------------

    if not os.path.exists(PASTA_ZIP):
        raise Exception(f"Pasta não encontrada: {PASTA_ZIP}")

    arquivos_zip = sorted([
        f for f in os.listdir(PASTA_ZIP)
        if f.endswith(".zip")
    ])

    if not arquivos_zip:
        raise Exception(f"Nenhum ZIP encontrado em: {PASTA_ZIP}")

    todos_inventarios = []

    for nome_zip in arquivos_zip:

        caminho_zip = os.path.join(PASTA_ZIP, nome_zip)

        print(f"Processando: {nome_zip}")

        inventarios = []

        with zipfile.ZipFile(caminho_zip) as z:

            # --------------------------------------------------
            # INVENTÁRIO
            # --------------------------------------------------

            arquivos = [
                f for f in z.namelist()
                if f.startswith("01_Inventario/") and f.endswith(".xlsx")
            ]

            for arquivo in arquivos:

                empresa, data_inventario = extrair_info_nome(arquivo.split("/")[-1])

                df = pd.read_excel(z.open(arquivo), header=1)

                df.columns = df.columns.str.strip().str.upper()

                df = df.rename(columns={
                    "CODIGO":                     "Codigo",
                    "DESCRICAO":                  "Descricao",
                    "QUANTIDADE INVENTARIADA":    "Qtd_Inventariada",
                    "QTD NA DATA DO INVENTARIO":  "Qtd_Protheus",
                    "DIFERENCA QUANTIDADE":       "Qtd_Divergente",
                    "DIFERENCA VALOR":            "Valor_Divergente"
                })

                # Remove linhas sem código
                df = df[df["Codigo"].notna()]

                # Protege contra valores inválidos no Codigo
                df["Codigo"] = pd.to_numeric(df["Codigo"], errors="coerce")
                df = df[df["Codigo"].notna()]
                df["Codigo"] = df["Codigo"].astype(int).astype(str).str.zfill(6)

                df["Empresa"]         = empresa
                df["Data_Inventario"] = data_inventario

                df["Qtd_Itens_Inventariados"] = 1
                df["Qtd_Itens_Divergentes"]   = (df["Qtd_Divergente"] != 0).astype(int)

                inventarios.append(df)

            inventario = pd.concat(inventarios, ignore_index=True)

            # --------------------------------------------------
            # EMPRESAS
            # --------------------------------------------------

            empresas = pd.read_excel(z.open("02_Empresas/02_Empresas.xlsx"))

            empresas["Empresa"] = (
                empresas["Empresa"]
                .astype(int)
                .astype(str)
                .str.zfill(4)
            )

            inventario["Empresa"] = (
                inventario["Empresa"]
                .astype(str)
                .str.zfill(4)
            )

            inventario = inventario.merge(
                empresas,
                on="Empresa",
                how="left"
            )

            inventario = inventario.rename(columns={
                "Empresa / Filial": "Nome_Empresa"
            })

        todos_inventarios.append(inventario)

    # ----------------------------------------------------------
    # CONSOLIDA TODOS OS ZIPs
    # ----------------------------------------------------------

    inventario_final = pd.concat(todos_inventarios, ignore_index=True)

    # ----------------------------------------------------------
    # ESTOQUE — join com valor unitário
    # ----------------------------------------------------------

    estoque = pd.read_parquet(CAMINHO_ESTOQUE)

    estoque["Produto"] = (
        pd.to_numeric(estoque["Produto"], errors="coerce")
        .dropna()
        .astype(int)
        .astype(str)
        .str.zfill(6)
    )

    # Protege contra divisão por zero
    estoque["Valor_Unitario"] = estoque.apply(
        lambda r: r["Custo Total"] / r["Saldo Atual"] if r["Saldo Atual"] > 0 else 0,
        axis=1
    )

    # Filtra apenas datas relevantes para evitar duplicatas no merge
    datas_inventario = inventario_final["Data_Inventario"].unique()
    estoque = estoque[estoque["Data Fechamento"].isin(datas_inventario)]

    estoque = estoque[["Data Fechamento", "Produto", "Valor_Unitario"]]

    inventario_final = inventario_final.merge(
        estoque,
        left_on=["Codigo", "Data_Inventario"],
        right_on=["Produto", "Data Fechamento"],
        how="left"
    )

    # ----------------------------------------------------------
    # CÁLCULOS
    # ----------------------------------------------------------

    inventario_final["Valor_Protheus"] = (
        inventario_final["Qtd_Protheus"] * inventario_final["Valor_Unitario"]
    )

    inventario_final["Valor_Inventariado"] = (
        inventario_final["Qtd_Inventariada"] * inventario_final["Valor_Unitario"]
    )

    # ----------------------------------------------------------
    # ORGANIZAÇÃO FINAL
    # ----------------------------------------------------------

    inventario_final = inventario_final[
        [
            "Data_Inventario",
            "Empresa",
            "Nome_Empresa",
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
        ]
    ]

    inventario_final = inventario_final.sort_values("Data_Inventario")

    Path("data/inventario").mkdir(parents=True, exist_ok=True)

    inventario_final.to_parquet(CAMINHO_SAIDA, index=False)

    print(f"Inventário processado com sucesso — {len(inventario_final)} registros salvos.")


if __name__ == "__main__":
    processar_zip()
