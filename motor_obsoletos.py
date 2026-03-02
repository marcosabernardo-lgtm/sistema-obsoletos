import pandas as pd
import zipfile
import io


# ============================================================
# NORMALIZAÇÃO EMPRESA
# ============================================================

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


# ============================================================
# MOTOR - BLOCO 1 (SOMENTE ESTOQUE)
# ============================================================

def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        arquivo_estoque = next(
            (n for n in z.namelist()
             if "02_Estoque_Atual" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_estoque:
            raise Exception("02_Estoque_Atual não encontrado no ZIP")

        with z.open(arquivo_estoque) as f:
            df_estoque = pd.read_excel(
                f,
                sheet_name="Detalhado",
                dtype={"Código": str}
            )

    # =====================================================
    # PADRONIZAÇÃO DE COLUNAS
    # =====================================================

    df_estoque = df_estoque.rename(columns={
        "Valor Total": "Custo Total",
        "Código": "Produto",
        "Descrição": "Descricao",
        "Quantidade": "Saldo Atual"
    })

    # =====================================================
    # NORMALIZA EMPRESA E FILIAL
    # =====================================================

    df_estoque["Empresa"] = df_estoque["Empresa"].apply(normalizar_empresa)
    df_estoque["Filial"] = df_estoque["Filial"].astype(str).str.title()

    df_estoque["Empresa / Filial"] = (
        df_estoque["Empresa"] + " / " + df_estoque["Filial"]
    )

    # =====================================================
    # PRODUTO (mantém zeros à esquerda)
    # =====================================================

    df_estoque["Produto"] = (
        df_estoque["Produto"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # =====================================================
    # ID ÚNICO
    # =====================================================

    df_estoque["ID_UNICO"] = (
        df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]
    )

    # =====================================================
    # DATA BASE
    # =====================================================

    data_base = pd.to_datetime(
        df_estoque["Data Fechamento"],
        dayfirst=True,
        errors="coerce"
    ).max()

    df_estoque["Data_Base"] = data_base

    # =====================================================
    # FORMATAÇÃO NUMÉRICA
    # =====================================================

    df_estoque["Saldo Atual"] = pd.to_numeric(
        df_estoque["Saldo Atual"], errors="coerce"
    )

    df_estoque["Custo Total"] = pd.to_numeric(
        df_estoque["Custo Total"], errors="coerce"
    )

    # =====================================================
    # REMOVER COLUNAS REDUNDANTES
    # =====================================================

    df_estoque = df_estoque.drop(columns=["Empresa", "Filial"])

    # =====================================================
    # ORGANIZAÇÃO FINAL DAS COLUNAS
    # Empresa / Filial logo após Data Fechamento
    # =====================================================

    colunas_ordenadas = [
        "Data Fechamento",
        "Empresa / Filial",
        "Tipo de Estoque",
        "Conta",
        "Produto",
        "Descricao",
        "Unid",
        "Saldo Atual",
        "Vlr Unit",
        "Custo Total",
        "ID_UNICO",
        "Data_Base"
    ]

    df_final = df_estoque[colunas_ordenadas].copy()

    # =====================================================
    # EXPORTAÇÃO
    # =====================================================

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()
