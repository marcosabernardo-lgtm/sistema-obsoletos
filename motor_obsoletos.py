import pandas as pd
import zipfile
import io

def executar_motor(uploaded_file):

    # ===============================
    # LEITURA DO ZIP
    # ===============================

    with zipfile.ZipFile(uploaded_file) as z:
        arquivos_excel = [f for f in z.namelist() if f.endswith(".xlsx")]

        if not arquivos_excel:
            raise Exception("Nenhum arquivo Excel encontrado dentro do ZIP.")

        nome_arquivo = arquivos_excel[0]

        with z.open(nome_arquivo) as excel_file:
            df_estoque = pd.read_excel(
                excel_file,
                sheet_name="Detalhado",
                dtype={"Código": str}
            )

    # ===============================
    # PADRONIZAÇÃO DE COLUNAS
    # ===============================

    df_estoque = df_estoque.rename(columns={
        "Valor Total": "Custo Total",
        "Código": "Produto",
        "Descrição": "Descricao",
        "Quantidade": "Saldo Atual"
    })

    # ===============================
    # NORMALIZAÇÃO EMPRESA
    # ===============================

    def normalizar_empresa(nome):
        nome = str(nome).upper()
        if "TOOLS" in nome: return "Tools"
        if "MAQUINAS" in nome: return "Maquinas"
        if "ALLSERVICE" in nome: return "Service"
        if "ROBOTICA" in nome: return "Robotica"
        return nome

    df_estoque["Empresa"] = df_estoque["Empresa"].apply(normalizar_empresa)

    # ===============================
    # AJUSTES DE CAMPOS
    # ===============================

    df_estoque["Filial"] = df_estoque["Filial"].astype(str).str.title()

    df_estoque["Empresa / Filial"] = (
        df_estoque["Empresa"] + " / " + df_estoque["Filial"]
    )

    df_estoque["Produto"] = (
        df_estoque["Produto"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Garante zero à esquerda
    df_estoque["Produto"] = df_estoque["Produto"].str.zfill(6)

    df_estoque["ID_UNICO"] = (
        df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]
    )

    # ===============================
    # DATA BASE
    # ===============================

    DataBase = pd.to_datetime(
        df_estoque["Data Fechamento"],
        dayfirst=True,
        errors="coerce"
    ).max()

    df_estoque["Data Base"] = DataBase

    # ===============================
    # EXPORTAÇÃO PARA EXCEL
    # ===============================

    buffer = io.BytesIO()
    df_estoque.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_estoque, buffer.getvalue()
