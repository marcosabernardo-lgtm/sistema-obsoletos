import pandas as pd
import zipfile
import io
from pathlib import Path


CAMINHO_ESTOQUE = "data/estoque/estoque_historico.parquet"


# ==========================================================
# EXTRAI EMPRESA E DATA DO NOME DO ARQUIVO
# ==========================================================

def extrair_info_nome(nome_arquivo):

    nome = Path(nome_arquivo).stem

    try:
        empresa         = nome[:4]
        dia             = int(nome[4:6])
        mes             = int(nome[6:8])
        ano             = int(nome[8:12])
        data            = pd.Timestamp(ano, mes, dia)
        data_fechamento = data + pd.offsets.MonthEnd(0)
    except Exception:
        raise ValueError(f"Nome de arquivo fora do padrão esperado: {nome_arquivo}")

    return empresa, data_fechamento


# ==========================================================
# MOTOR INVENTÁRIO — processa 1 ZIP por vez
# ==========================================================

def executar_motor_inventario(caminho_zip):

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
                "CODIGO":                    "Codigo",
                "DESCRICAO":                 "Descricao",
                "QUANTIDADE INVENTARIADA":   "Qtd_Inventariada",
                "QTD NA DATA DO INVENTARIO": "Qtd_Protheus",
                "DIFERENCA QUANTIDADE":      "Qtd_Divergente",
                "DIFERENCA VALOR":           "Valor_Divergente"
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
    datas_inventario = inventario["Data_Inventario"].unique()
    estoque = estoque[estoque["Data Fechamento"].isin(datas_inventario)]

    estoque = estoque[["Data Fechamento", "Produto", "Valor_Unitario"]]

    inventario = inventario.merge(
        estoque,
        left_on=["Codigo", "Data_Inventario"],
        right_on=["Produto", "Data Fechamento"],
        how="left"
    )

    # ----------------------------------------------------------
    # CÁLCULOS
    # ----------------------------------------------------------

    inventario["Valor_Protheus"] = (
        inventario["Qtd_Protheus"] * inventario["Valor_Unitario"]
    )

    inventario["Valor_Inventariado"] = (
        inventario["Qtd_Inventariada"] * inventario["Valor_Unitario"]
    )

    # ----------------------------------------------------------
    # ORGANIZAÇÃO FINAL
    # ----------------------------------------------------------

    df_final = inventario[
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
    ].copy()

    df_final = df_final.sort_values("Data_Inventario")

    # ----------------------------------------------------------
    # EXPORTAÇÃO
    # ----------------------------------------------------------

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
