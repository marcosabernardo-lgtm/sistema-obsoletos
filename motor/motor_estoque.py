import pandas as pd
import zipfile
import io
from collections import defaultdict

# ==========================================================
# NORMALIZA EMPRESA
# ==========================================================

def normalizar_empresa(nome):
    nome = str(nome).upper()
    if "TOOLS" in nome: return "Tools"
    if "MAQUINAS" in nome: return "Maquinas"
    if "ALLSERVICE" in nome: return "Service"
    if "ROBOTICA" in nome: return "Robotica"
    return nome

# ==========================================================
# MOTOR EVOLUÇÃO ESTOQUE
# ==========================================================

def executar_motor_estoque(caminho_zip):
    with zipfile.ZipFile(caminho_zip, "r") as z:

        # ------------------------------------------------------
        # 1. LEITURA DA BASE PRINCIPAL (ESTOQUE ATUAL)
        # ------------------------------------------------------
        arquivo_estoque = next(
            (n for n in z.namelist() if "02_Estoque_Atual" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_estoque:
            raise Exception("Arquivo 02_Estoque_Atual não encontrado no ZIP")

        with z.open(arquivo_estoque) as f:
            df = pd.read_excel(f, sheet_name="Detalhado", dtype={"Código": str}, engine="openpyxl")
        
        # Limpar espaços invisíveis nos nomes das colunas (Essencial)
        df.columns = df.columns.astype(str).str.strip()

        # ------------------------------------------------------
        # 2. DETECÇÃO ROBUSTA DO TIPO DE ESTOQUE
        # ------------------------------------------------------
        # Procura por qualquer coluna que contenha "Tipo" e "Estoque" no nome
        col_tipo_detectada = next(
            (c for c in df.columns if "TIPO" in c.upper() and "ESTOQUE" in c.upper()), 
            None
        )

        if col_tipo_detectada:
            df = df.rename(columns={col_tipo_detectada: "Tipo de Estoque"})
            # Normaliza para Title Case: "Em Estoque", "Em Processo", "Em Fabricação"
            df["Tipo de Estoque"] = df["Tipo de Estoque"].fillna("Em Estoque").astype(str).str.strip().str.title()
        else:
            # Fallback caso a coluna não exista no Excel original
            df["Tipo de Estoque"] = "Em Estoque"

        # ------------------------------------------------------
        # 3. TRATAMENTO DE MÁQUINAS USADAS (PASTA 06)
        # ------------------------------------------------------
        arquivos_usadas = [n for n in z.namelist() if "06_Usadas/" in n and n.lower().endswith(".xlsx")]
        usadas_tipo_por_empresa = {}

        for nome in arquivos_usadas:
            nome_upper = nome.upper()
            if "TOOLS" in nome_upper: empresa = "Tools"
            elif "MAQUINAS" in nome_upper: empresa = "Maquinas"
            elif "ROBOTICA" in nome_upper: empresa = "Robotica"
            elif "SERVICE" in nome_upper: empresa = "Service"
            else: continue

            with z.open(nome) as f:
                df_u = pd.read_excel(f, dtype=str, engine="openpyxl")

            df_u.columns = df_u.columns.str.strip()
            por_tipo = defaultdict(set)

            if "Tipo" in df_u.columns:
                df_u["Codigo"] = df_u["Codigo"].astype(str).str.strip().str.replace(".0", "", regex=False)
                df_u["Tipo"] = df_u["Tipo"].astype(str).str.strip().str.title()
                for _, row in df_u.iterrows():
                    por_tipo[row["Tipo"]].add(row["Codigo"])
            else:
                if "Codigo" in df_u.columns:
                    codigos = set(df_u["Codigo"].astype(str).str.strip().str.replace(".0", "", regex=False))
                    por_tipo["Maquina Usada"] = codigos

            usadas_tipo_por_empresa[empresa] = por_tipo

    # ------------------------------------------------------
    # 4. TRATAMENTO DA BASE FINAL
    # ------------------------------------------------------
    df = df.rename(columns={
        "Valor Total": "Custo Total",
        "Código": "Produto",
        "Descrição": "Descricao",
        "Quantidade": "Saldo Atual"
    })

    # Normalização de Conta e Localização
    df["Conta"] = df["Conta"].astype(str).str.strip().str.title()
    df["Empresa_Nome"] = df["Empresa"].apply(normalizar_empresa)
    df["Filial_Nome"] = df["Filial"].astype(str).str.title()
    df["Empresa / Filial"] = df["Empresa_Nome"] + " / " + df["Filial_Nome"]

    # Limpeza de Códigos de Produto
    df["Produto"] = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)

    # Conversão Numérica
    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"], errors="coerce")

    # ------------------------------------------------------
    # 5. MARCAR TIPO DA MAQUINA (CONTA)
    # ------------------------------------------------------
    if usadas_tipo_por_empresa:
        for empresa, por_tipo in usadas_tipo_por_empresa.items():
            for tipo, codigos in por_tipo.items():
                mask = (
                    df["Empresa / Filial"].str.startswith(empresa)
                    & df["Produto"].isin(codigos)
                )
                df.loc[mask, "Conta"] = tipo

    # ------------------------------------------------------
    # 6. ORGANIZA COLUNAS E EXPORTA
    # ------------------------------------------------------
    colunas_finais = [
        "Data Fechamento", "Empresa / Filial", "Tipo de Estoque", 
        "Conta", "Produto", "Descricao", "Saldo Atual", "Custo Total"
    ]

    # Garante que todas as colunas existam
    for col in colunas_finais:
        if col not in df.columns: df[col] = ""

    df_final = df[colunas_finais].copy()

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()