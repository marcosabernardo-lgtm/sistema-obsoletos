import pandas as pd
import io
import numpy as np
import httpx
import streamlit as st
from supabase import create_client, Client, ClientOptions
from collections import defaultdict

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
# ESTOQUE
# Lógica original: normalizar_empresa() + str.title() na filial
# Gera: "Tools / Filial", "Robotica / Matriz", etc.
# ==========================================================

def normalizar_empresa(nome):
    nome = str(nome).upper()
    if "TOOLS" in nome:      return "Tools"
    if "MAQUINAS" in nome:   return "Maquinas"
    if "ALLSERVICE" in nome: return "Service"
    if "ROBOTICA" in nome:   return "Robotica"
    return nome


def executar_estoque(supabase: Client, data_fechamento: str) -> pd.DataFrame:

    print("📦 Carregando estoque_fechamentos...")
    df = ler_tabela(supabase, "estoque_fechamentos", {"data_fechamento": data_fechamento})
    print(f"   → {len(df)} registros")

    print("📦 Carregando estoque_usadas...")
    df_usadas = ler_tabela(supabase, "estoque_usadas")
    print(f"   → {len(df_usadas)} registros")

    # Monta dicionário de usadas igual ao original
    usadas_tipo_por_empresa = {}
    for _, row in df_usadas.iterrows():
        empresa = str(row.get("empresa", "")).strip()
        tipo    = str(row.get("tipo", "Maquina Usada")).strip().title()
        codigo  = str(row.get("codigo", "")).strip().replace(".0", "")
        if empresa not in usadas_tipo_por_empresa:
            usadas_tipo_por_empresa[empresa] = {}
        usadas_tipo_por_empresa[empresa][codigo] = tipo

    # Renomear colunas do Supabase para o padrão do motor original
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
    if "Tipo de Estoque" in df.columns:
        df["Tipo de Estoque"] = df["Tipo de Estoque"].fillna("Não Informado").astype(str).str.strip().str.title()
    else:
        df["Tipo de Estoque"] = "Em Estoque"

    # Igual ao motor original:
    # normalizar_empresa() + str.title() na filial → "Tools / Filial"
    df["Vlr Unit"]  = pd.to_numeric(df["Vlr Unit"], errors="coerce").fillna(0)
    df["Empresa"]   = df["Empresa"].apply(normalizar_empresa)
    df["Filial"]    = df["Filial"].astype(str).str.title()
    df["Empresa / Filial"] = df["Empresa"] + " / " + df["Filial"]
    # Motor antigo lia produto como número (int) do Excel → sem zeros à esquerda
    # No Supabase vem como string com zeros → converter igual
    df["Produto"] = pd.to_numeric(df["Produto"], errors="coerce").fillna(0).astype(int).astype(str)
    df["ID_UNICO"]  = df["Empresa / Filial"] + "|" + df["Produto"]
    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"], errors="coerce")

    if "Conta" in df.columns:
        df["Conta"] = df["Conta"].astype(str).str.strip().str.title()

    # Marcar usadas
    if usadas_tipo_por_empresa:
        for empresa, tipo_map in usadas_tipo_por_empresa.items():
            for codigo, tipo in tipo_map.items():
                mask = (
                    df["Empresa / Filial"].str.startswith(empresa) &
                    (df["Produto"] == codigo)
                )
                df.loc[mask, "Conta"] = tipo

    df = df.drop(columns=["Empresa", "Filial", "id", "created_at", "updated_at"], errors="ignore")

    colunas = df.columns.tolist()
    nova_ordem = ["Data Fechamento", "Empresa / Filial"]
    demais = [c for c in colunas if c not in nova_ordem]

    return df[nova_ordem + demais]


# ==========================================================
# MOVIMENTAÇÕES
# Lógica original: Mesclado = empresa + " " + filial
# Merge com df_empresas["Mesclado"] → "Empresa / Filial"
# No Supabase: empresa="Robotica", filial="00" → "Robotica 00"
# estoque_empresas: id="Robotica 00" → empresa_filial="Robotica / Matriz"
# ==========================================================

def executar_movimentacoes(supabase: Client, df_empresas: pd.DataFrame) -> pd.DataFrame:

    print("📦 Carregando movimentos...")
    df = ler_tabela(supabase, "movimentos")
    print(f"   → {len(df)} registros")

    if df.empty:
        return pd.DataFrame(columns=["ID_UNICO", "Ult_Mov"])

    df["Produto"] = pd.to_numeric(df["produto"], errors="coerce").fillna(0).astype(int).astype(str)
    df["Filial"]  = df["filial"].astype(str).str.strip()
    df["Mesclado"] = df["empresa"].astype(str).str.strip() + " " + df["Filial"]

    df = df.merge(
        df_empresas[["Mesclado", "Empresa / Filial"]],
        on="Mesclado",
        how="left"
    )

    df["DT Emissao"] = pd.to_datetime(df["dt_emissao"], errors="coerce")
    df["ID_UNICO"]   = df["Empresa / Filial"] + "|" + df["Produto"]

    df = df[df["DT Emissao"].notna()]

    print(f"   → {df['ID_UNICO'].nunique()} IDs únicos")

    return (
        df.groupby("ID_UNICO", as_index=False)["DT Emissao"]
        .max()
        .rename(columns={"DT Emissao": "Ult_Mov"})
    )


# ==========================================================
# ENTRADAS / SAÍDAS
# Lógica original: Mesclado = empresa + " " + FILIAL
# Merge com df_empresas → "Empresa / Filial"
# ==========================================================

def executar_entradas_saidas(supabase: Client, df_empresas: pd.DataFrame) -> pd.DataFrame:

    print("📦 Carregando entradas_saidas...")
    df = ler_tabela(supabase, "entradas_saidas")
    print(f"   → {len(df)} registros")

    if df.empty:
        return pd.DataFrame(columns=["ID_UNICO", "Ult_Entrada", "Ult_Saida"])

    df["Produto"]  = pd.to_numeric(df["produto"], errors="coerce").fillna(0).astype(int).astype(str)
    df["Filial"]   = df["filial"].astype(str).str.strip()
    df["Mesclado"] = df["empresa"].astype(str).str.strip() + " " + df["Filial"]

    df = df.merge(
        df_empresas[["Mesclado", "Empresa / Filial"]],
        on="Mesclado",
        how="left"
    )

    df["DIGITACAO"] = pd.to_datetime(df["digitacao"], errors="coerce")
    df["ID_UNICO"]  = df["Empresa / Filial"] + "|" + df["Produto"]

    df_entrada = df[df["tipo"] == "ENTRADA"].copy()
    df_saida   = df[df["tipo"] == "SAIDA"].copy()

    df_entrada["DtEnt"] = df_entrada["DIGITACAO"]
    df_saida["DtSai"]   = df_saida["DIGITACAO"]

    lista = []
    if not df_entrada.empty:
        lista.append(df_entrada[["ID_UNICO", "DtEnt"]].assign(DtSai=pd.NaT))
    if not df_saida.empty:
        lista.append(df_saida[["ID_UNICO", "DtSai"]].assign(DtEnt=pd.NaT))

    if not lista:
        return pd.DataFrame(columns=["ID_UNICO", "Ult_Entrada", "Ult_Saida"])

    df_all = pd.concat(lista, ignore_index=True)

    return df_all.groupby("ID_UNICO", as_index=False).agg(
        Ult_Entrada=("DtEnt", "max"),
        Ult_Saida=("DtSai", "max")
    )


# ==========================================================
# MOTOR FINAL
# ==========================================================

def executar_motor(data_fechamento: str = None):
    """
    Motor principal de obsoletos — lê tudo do Supabase.
    Retorna: df_final (DataFrame), buffer Excel (bytes)
    """
    supabase = get_supabase()

    # Busca data mais recente se não informada
    if not data_fechamento:
        res = supabase.table("estoque_fechamentos") \
            .select("data_fechamento") \
            .order("data_fechamento", desc=True) \
            .limit(1) \
            .execute()
        data_fechamento = res.data[0]["data_fechamento"]
        print(f"📅 Fechamento mais recente: {data_fechamento}")

    # Carrega estoque_empresas — equivalente ao 05_Empresas.xlsx original
    # id="Robotica 00" → empresa_filial="Robotica / Matriz"
    print("📦 Carregando estoque_empresas...")
    df_empresas = ler_tabela(supabase, "estoque_empresas")
    df_empresas = df_empresas.rename(columns={
        "id":            "Mesclado",
        "empresa_filial": "Empresa / Filial"
    })
    df_empresas["Mesclado"]        = df_empresas["Mesclado"].str.strip()
    df_empresas["Empresa / Filial"] = df_empresas["Empresa / Filial"].str.strip()
    print(f"   → {len(df_empresas)} registros")

    # Executa sub-motores
    df_estoque = executar_estoque(supabase, data_fechamento)
    df_mov     = executar_movimentacoes(supabase, df_empresas)
    df_es      = executar_entradas_saidas(supabase, df_empresas)

    # ----------------------------------------------------------
    # MERGE FINAL — igual ao motor original
    # ----------------------------------------------------------
    df_final = df_estoque.merge(df_mov, on="ID_UNICO", how="left")
    df_final = df_final.merge(df_es,   on="ID_UNICO", how="left")

    df_final["Ult_Movimentacao"] = df_final[["Ult_Mov", "Ult_Entrada", "Ult_Saida"]].max(axis=1)
    df_final["Ult_Movimentacao"] = pd.to_datetime(df_final["Ult_Movimentacao"], errors="coerce")

    def origem(row):
        if row["Ult_Movimentacao"] == row["Ult_Saida"]:   return "Ult_Saida"
        if row["Ult_Movimentacao"] == row["Ult_Entrada"]: return "Ult_Entrada"
        if row["Ult_Movimentacao"] == row["Ult_Mov"]:     return "Ult_Mov"
        return None

    df_final["Origem Mov"] = df_final.apply(origem, axis=1)
    df_final = df_final.drop(columns=["Ult_Mov", "Ult_Entrada", "Ult_Saida"])

    df_final["Tipo de Estoque"] = df_final["Tipo de Estoque"].astype(str).str.title()

    CONTA_CORRECOES = {
        "MR":                  "Material Revenda",
        "MATERIAL REVENDA":    "Material Revenda",
        "MATERIAL DE REVENDA": "Material De Revenda",
    }
    df_final["Conta"] = df_final["Conta"].astype(str).str.strip().str.upper().map(
        lambda x: CONTA_CORRECOES.get(x, x)
    ).str.title()

    df_final = df_final.drop(columns=["ID_UNICO"], errors="ignore")

    DataBase = pd.to_datetime(df_final["Data Fechamento"].iloc[0])

    df_final["Dias Sem Mov"] = (DataBase - df_final["Ult_Movimentacao"]).dt.days.fillna(9999)

    df_final["Meses Ult Mov"] = np.where(
        df_final["Ult_Movimentacao"].notna(),
        (DataBase.year  - df_final["Ult_Movimentacao"].dt.year)  * 12 +
        (DataBase.month - df_final["Ult_Movimentacao"].dt.month),
        np.nan
    )

    df_final["Status Estoque"] = np.where(
        df_final["Tipo de Estoque"].str.contains("Fabric", case=False),
        "Até 6 meses",
        np.where(
            df_final["Ult_Movimentacao"].isna() | (df_final["Meses Ult Mov"] > 6),
            "Obsoleto",
            "Até 6 meses"
        )
    )

    def status_mov(row):
        if "Fabric" in str(row["Tipo de Estoque"]): return "Até 6 meses"
        if pd.isna(row["Meses Ult Mov"]):           return "Sem Movimento"
        if row["Meses Ult Mov"] <= 6:               return "Até 6 meses"
        if row["Meses Ult Mov"] <= 12:              return "Até 1 ano"
        if row["Meses Ult Mov"] <= 24:              return "+ 1 ano"
        return "+ 2 anos"

    df_final["Status do Movimento"] = df_final.apply(status_mov, axis=1)

    def formatar(row):
        if "Fabric" in str(row["Tipo de Estoque"]): return "Em fabricação"
        if pd.isna(row["Ult_Movimentacao"]):         return "Sem movimento"
        dias      = (DataBase - row["Ult_Movimentacao"]).days
        anos      = dias // 365
        meses     = (dias % 365) // 30
        dias_rest = (dias % 365) % 30
        return f"{anos} anos {meses} meses {dias_rest} dias"

    df_final["Ano Meses Dias"] = df_final.apply(formatar, axis=1)

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    print(f"✅ Motor concluído — {len(df_final)} registros")
    return df_final, buffer.getvalue()