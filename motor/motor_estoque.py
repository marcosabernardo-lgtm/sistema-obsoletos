import pandas as pd
import io
import numpy as np
from collections import defaultdict
import httpx
import streamlit as st
from supabase import create_client, Client, ClientOptions

# ==========================================================
# CONEXÃO SUPABASE
# ==========================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

def get_supabase() -> Client:
    http_client = httpx.Client(verify=False, timeout=60.0)
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(httpx_client=http_client))

def ler_tabela(supabase: Client, tabela: str, filtros: dict = None) -> pd.DataFrame:
    """Lê tabela completa do Supabase em páginas de 1000."""
    registros = []
    pagina = 0
    while True:
        query = supabase.table(tabela).select("*")
        if filtros:
            for col, val in filtros.items():
                query = query.eq(col, val)
        res = query.range(pagina * 1000, (pagina + 1) * 1000 - 1).execute()
        registros.extend(res.data)
        if len(res.data) < 1000:
            break
        pagina += 1
    return pd.DataFrame(registros)


# ==========================================================
# NORMALIZA EMPRESA
# ==========================================================

def normalizar_empresa(nome):
    nome = str(nome).upper()
    if "TOOLS" in nome:    return "Tools"
    if "MAQUINAS" in nome: return "Maquinas"
    if "ALLSERVICE" in nome or "SERVICE" in nome: return "Service"
    if "ROBOTICA" in nome: return "Robotica"
    return nome

EMPRESA_FILIAL_MAP_NORM = {
    ("TOOLS",    "00"): "Tools / Matriz",
    ("TOOLS",    "01"): "Tools / Filial",
    ("MAQUINAS", "00"): "Maquinas / Matriz",
    ("MAQUINAS", "01"): "Maquinas / Filial",
    ("MAQUINAS", "02"): "Maquinas / Jundiai",
    ("ROBOTICA", "00"): "Robotica / Matriz",
    ("ROBOTICA", "01"): "Robotica / Filial Jaragua",
    ("SERVICE",  "01"): "Service / Matriz",
    ("SERVICE",  "02"): "Service / Filial",
    ("SERVICE",  "03"): "Service / Caxias",
    ("SERVICE",  "04"): "Service / Jundiai",
}

def mapear_empresa_filial_norm(empresa: str, filial: str) -> str:
    key = (str(empresa).strip().upper(), str(filial).strip().zfill(2))
    return EMPRESA_FILIAL_MAP_NORM.get(key, f"{empresa} / {filial}")
    ("ALLTECH TOOLS DO BRASIL LTDA",         "MATRIZ"):         "Tools / Matriz",
    ("ALLTECH TOOLS DO BRASIL LTDA",         "FILIAL"):         "Tools / Filial",
    ("ALLTECH MAQUINAS E EQUIPAMENTOS LTDA", "MATRIZ"):         "Maquinas / Matriz",
    ("ALLTECH MAQUINAS E EQUIPAMENTOS LTDA", "FILIAL"):         "Maquinas / Filial",
    ("ALLTECH MAQUINAS E EQUIPAMENTOS LTDA", "JUNDIAI"):        "Maquinas / Jundiai",
    ("ALLTECH ROBOTICA E AUTOMACAO LTDA",    "MATRIZ"):         "Robotica / Matriz",
    ("ALLTECH ROBOTICA E AUTOMACAO LTDA",    "FILIAL JARAGUA"): "Robotica / Filial Jaragua",
    ("ALLSERVICE MANUTENCAO",                "MATRIZ"):         "Service / Matriz",
    ("ALLSERVICE MANUTENCAO",                "FILIAL"):         "Service / Filial",
    ("ALLSERVICE MANUTENCAO",                "CAXIAS"):         "Service / Caxias",
    ("ALLSERVICE MANUTENCAO LTDA",           "JUNDIAI"):        "Service / Jundiai",
}

def mapear_empresa_filial(empresa: str, filial: str) -> str:
    key = (str(empresa).strip().upper(), str(filial).strip().upper())
    return EMPRESA_FILIAL_MAP.get(key, f"{empresa} / {filial}")


# ==========================================================
# MOTOR EVOLUÇÃO ESTOQUE
# ==========================================================

def executar_motor_estoque(data_fechamento: str = None):
    """
    Lê estoque do Supabase e retorna DataFrame + buffer Excel.

    Parâmetros:
        data_fechamento: ex "2026-03-31". Se None, usa o mais recente.
    """
    supabase = get_supabase()

    # ----------------------------------------------------------
    # 1. LEITURA DO ESTOQUE
    # ----------------------------------------------------------
    print("📦 Carregando estoque_fechamentos...")

    if not data_fechamento:
        res = supabase.table("estoque_fechamentos") \
            .select("data_fechamento") \
            .order("data_fechamento", desc=True) \
            .limit(1) \
            .execute()
        data_fechamento = res.data[0]["data_fechamento"]
        print(f"   → Fechamento mais recente: {data_fechamento}")

    df = ler_tabela(supabase, "estoque_fechamentos", {"data_fechamento": data_fechamento})
    print(f"   → {len(df)} registros")

    # ----------------------------------------------------------
    # 3. LEITURA DE MÁQUINAS USADAS
    # ----------------------------------------------------------
    print("📦 Carregando estoque_usadas...")
    df_usadas = ler_tabela(supabase, "estoque_usadas")
    print(f"   → {len(df_usadas)} registros")

    usadas_tipo_por_empresa = defaultdict(lambda: defaultdict(set))
    for _, row in df_usadas.iterrows():
        empresa = str(row.get("empresa", "")).strip()
        tipo    = str(row.get("tipo",    "Maquina Usada")).strip().title()
        codigo  = str(row.get("codigo",  "")).strip().replace(".0", "")
        usadas_tipo_por_empresa[empresa][tipo].add(codigo)

    # ----------------------------------------------------------
    # 4. TRATAMENTO DA BASE
    # ----------------------------------------------------------
    df = df.rename(columns={
        "data_fechamento": "Data Fechamento",
        "empresa":         "Empresa",
        "filial":          "Filial",
        "tipo_de_estoque": "Tipo de Estoque",
        "conta":           "Conta",
        "produto":         "Produto",
        "descricao":       "Descricao",
        "unid":            "Unid",
        "saldo_atual":     "Saldo Atual",
        "vlr_unit":        "Vlr Unit",
        "custo_total":     "Custo Total",
    })

    # Tipo de Estoque
    df["Tipo de Estoque"] = df["Tipo de Estoque"].fillna("Em Estoque").astype(str).str.strip().str.title()

    # Empresa / Filial via mapeamento normalizado
    df["Empresa / Filial"] = df.apply(
        lambda r: mapear_empresa_filial_norm(r["Empresa"], r["Filial"]), axis=1
    )

    # Produto
    df["Produto"] = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)
    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]

    # Numéricos
    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)
    df["Vlr Unit"]    = pd.to_numeric(df["Vlr Unit"],    errors="coerce").fillna(0)
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"], errors="coerce")

    # Conta
    if "Conta" in df.columns:
        df["Conta"] = df["Conta"].astype(str).str.strip().str.title()

    # ----------------------------------------------------------
    # 5. MARCAR TIPO DA MÁQUINA (CONTA) pelas usadas
    # ----------------------------------------------------------
    for empresa, por_tipo in usadas_tipo_por_empresa.items():
        for tipo, codigos in por_tipo.items():
            mask = (
                df["Empresa / Filial"].str.startswith(empresa) &
                df["Produto"].isin(codigos)
            )
            df.loc[mask, "Conta"] = tipo

    # ----------------------------------------------------------
    # 6. ORGANIZA E EXPORTA
    # ----------------------------------------------------------
    df = df.drop(columns=["Empresa", "Filial", "Mesclado"], errors="ignore")

    colunas_finais = [
        "Data Fechamento", "Empresa / Filial", "Tipo de Estoque",
        "Conta", "Produto", "Descricao", "Unid", "Saldo Atual", "Vlr Unit", "Custo Total"
    ]
    for col in colunas_finais:
        if col not in df.columns:
            df[col] = ""

    df_final = df[colunas_finais].copy()

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    return df_final, buffer.getvalue()