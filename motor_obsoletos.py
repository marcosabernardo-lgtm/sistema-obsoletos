import pandas as pd
import zipfile
import io

def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # 🔎 procurar arquivo dentro da pasta 02_Estoque_Atual
        arquivos_estoque = [
            f for f in z.namelist()
            if f.startswith("02_Estoque_Atual")
            and f.lower().endswith(".xlsx")
        ]

        if not arquivos_estoque:
            raise Exception("Arquivo de estoque não encontrado na pasta 02_Estoque_Atual dentro do ZIP")

        caminho_estoque = arquivos_estoque[0]

        with z.open(caminho_estoque) as arquivo_excel:
            df_estoque = pd.read_excel(
                arquivo_excel,
                sheet_name="Detalhado",
                dtype={"Código": str}
            )

    # ================================
    # RENOMEAR COLUNAS
    # ================================

    df_estoque = df_estoque.rename(columns={
        "Valor Total": "Custo Total",
        "Código": "Produto",
        "Descrição": "Descricao",
        "Quantidade": "Saldo Atual"
    })

    # ================================
    # NORMALIZA EMPRESA
    # ================================

    def normalizar_empresa(nome):
        nome = str(nome).upper()
        if "TOOLS" in nome: return "Tools"
        if "MAQUINAS" in nome: return "Maquinas"
        if "ALLSERVICE" in nome: return "Service"
        if "ROBOTICA" in nome: return "Robotica"
        return nome

    df_estoque["Empresa"] = df_estoque["Empresa"].apply(normalizar_empresa)

    # ================================
    # AJUSTES PADRÃO
    # ================================

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

    # manter zero à esquerda
    df_estoque["Produto"] = df_estoque["Produto"].str.zfill(6)

    # garantir numéricos corretos
    df_estoque["Saldo Atual"] = pd.to_numeric(df_estoque["Saldo Atual"], errors="coerce")
    df_estoque["Custo Total"] = pd.to_numeric(df_estoque["Custo Total"], errors="coerce")

    df_estoque["ID_UNICO"] = (
        df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]
    )

    # Data base
    DataBase = pd.to_datetime(
        df_estoque["Data Fechamento"],
        dayfirst=True,
        errors="coerce"
    ).max()

    df_estoque["Data_Base"] = DataBase

    # ================================
    # EXPORTAÇÃO
    # ================================

    buffer = io.BytesIO()
    df_estoque.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_estoque, buffer.getvalue()
