import pandas as pd
import io
import numpy as np
import streamlit as st
from supabase import create_client


# ==========================================================
# CLIENTE SUPABASE
# ==========================================================

def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ==========================================================
# ESTOQUE
# ==========================================================

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


def executar_estoque():

    sb = get_supabase()

    # --- Último fechamento ---
    resp_data = sb.table("estoque_fechamentos") \
        .select("data_fechamento") \
        .order("data_fechamento", desc=True) \
        .limit(1) \
        .execute()

    if not resp_data.data:
        raise Exception("Nenhum fechamento encontrado em estoque_fechamentos")

    ultima_data = resp_data.data[0]["data_fechamento"]

    # --- Carrega o fechamento ---
    resp = sb.table("estoque_fechamentos") \
        .select("data_fechamento, empresa, filial, tipo_de_estoque, conta, produto, descricao, unid, saldo_atual, vlr_unit, custo_total") \
        .eq("data_fechamento", ultima_data) \
        .execute()

    df = pd.DataFrame(resp.data)

    # --- Renomeia colunas ---
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

    # --- Normaliza empresa e filial (mesmo padrão do backup) ---
    df["Empresa"] = df["Empresa"].apply(normalizar_empresa)
    df["Filial"]  = df["Filial"].astype(str).str.strip().str.title()

    # Empresa / Filial legível → "Service / Filial", "Tools / Matriz" etc
    # Esse é o mesmo valor que estoque_empresas.empresa_filial
    # e que movimentos vai espelhar via merge com estoque_empresas
    df["Empresa / Filial"] = df["Empresa"] + " / " + df["Filial"]
    df["Produto"]          = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)
    df["ID_UNICO"]         = df["Empresa / Filial"] + "|" + df["Produto"]

    # --- Tipo de Estoque ---
    df["Tipo de Estoque"] = df["Tipo de Estoque"].fillna("Não Informado").astype(str).str.strip().str.title()

    # --- Conta ---
    df["Conta"] = df["Conta"].astype(str).str.strip().str.title()

    # --- Numéricos ---
    df["Vlr Unit"]    = pd.to_numeric(df["Vlr Unit"],    errors="coerce").fillna(0)
    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)

    # --- estoque_usadas: sobrescreve Conta com tipo da usada ---
    resp_usadas = sb.table("estoque_usadas") \
        .select("codigo, tipo, empresa") \
        .execute()

    df_usadas = pd.DataFrame(resp_usadas.data)

    if not df_usadas.empty:
        df_usadas["codigo"]  = df_usadas["codigo"].astype(str).str.strip().str.replace(".0", "", regex=False)
        df_usadas["tipo"]    = df_usadas["tipo"].astype(str).str.strip().str.title()
        df_usadas["empresa"] = df_usadas["empresa"].astype(str).str.strip()

        for _, row_u in df_usadas.iterrows():
            mask = (
                df["Empresa / Filial"].str.startswith(row_u["empresa"]) &
                (df["Produto"] == row_u["codigo"])
            )
            df.loc[mask, "Conta"] = row_u["tipo"]

    df = df.drop(columns=["Empresa", "Filial"])

    nova_ordem = ["Data Fechamento", "Empresa / Filial"]
    demais     = [c for c in df.columns if c not in nova_ordem]

    return df[nova_ordem + demais]


# ==========================================================
# MOVIMENTACOES        <- ETAPA 2 (ainda nao implementada)
# ==========================================================

# def executar_movimentacoes(): ...


# ==========================================================
# ENTRADAS / SAIDAS    <- ETAPA 3 (ainda nao implementada)
# ==========================================================

# def executar_entradas_saidas(): ...


# ==========================================================
# MOTOR FINAL          <- ETAPA 4 (ainda nao implementada)
# ==========================================================

# def executar_motor(): ...


# ==========================================================
# MOVIMENTACOES
# ==========================================================
# Backup: lia 04_Movimento/*.xlsx (Robotica e Service)
#         montava Mesclado = empresa + " " + filial
#         merge com 05_Empresas → pega Empresa / Filial
#         ID_UNICO = "Robotica / Matriz|produto"
#
# Supabase: movimentos tem empresa="Robotica", filial="00"
#           estoque_empresas tem id="Robotica 00" → empresa_filial="Robotica / Matriz"
#           mesmo merge, mesma chave
# ==========================================================

def executar_movimentacoes():

    sb = get_supabase()

    # --- Carrega estoque_empresas para o de/para ---
    resp_emp = sb.table("estoque_empresas") \
        .select("id, empresa_filial") \
        .execute()

    df_emp = pd.DataFrame(resp_emp.data)
    df_emp["id"]             = df_emp["id"].astype(str).str.strip()
    df_emp["empresa_filial"] = df_emp["empresa_filial"].astype(str).str.strip()

    # --- Carrega movimentos ---
    resp = sb.table("movimentos") \
        .select("empresa, filial, produto, dt_emissao") \
        .execute()

    df = pd.DataFrame(resp.data)

    if df.empty:
        return pd.DataFrame(columns=["ID_UNICO", "Ult_Mov"])

    # --- Monta Mesclado = "Robotica 00" → igual ao backup ---
    df["Mesclado"] = df["empresa"].astype(str).str.strip() + " " + df["filial"].astype(str).str.strip()
    df["Produto"]  = df["produto"].astype(str).str.strip()

    # --- Merge com estoque_empresas para pegar Empresa / Filial legível ---
    df = df.merge(
        df_emp.rename(columns={"id": "Mesclado", "empresa_filial": "Empresa / Filial"}),
        on="Mesclado",
        how="left"
    )

    df["DT Emissao"] = pd.to_datetime(df["dt_emissao"], errors="coerce")
    df["ID_UNICO"]   = df["Empresa / Filial"] + "|" + df["Produto"]

    df = df[df["DT Emissao"].notna()]

    return (
        df.groupby("ID_UNICO", as_index=False)["DT Emissao"]
        .max()
        .rename(columns={"DT Emissao": "Ult_Mov"})
    )


# ==========================================================
# ENTRADAS / SAIDAS
# ==========================================================
# Backup: lia 01_Entradas_Saidas/*.xlsx (abas ENTRADA e SAIDA)
#         filtrava ESTOQUE == "S"
#         montava Mesclado = empresa + " " + filial
#         merge com 05_Empresas → pega Empresa / Filial
#         ID_UNICO = "Empresa / Filial|produto"
#
# Supabase: entradas_saidas tem empresa, filial (já normalizados)
#           campo tipo = "ENTRADA" ou "SAIDA"
#           campo estoque = "S" para filtrar
#           mesmo merge com estoque_empresas
# ==========================================================

def executar_entradas_saidas():

    sb = get_supabase()

    # --- Carrega estoque_empresas para o de/para ---
    resp_emp = sb.table("estoque_empresas") \
        .select("id, empresa_filial") \
        .execute()

    df_emp = pd.DataFrame(resp_emp.data)
    df_emp["id"]             = df_emp["id"].astype(str).str.strip()
    df_emp["empresa_filial"] = df_emp["empresa_filial"].astype(str).str.strip()

    # --- Carrega entradas_saidas (só estoque) ---
    resp = sb.table("entradas_saidas") \
        .select("empresa, filial, produto, tipo, digitacao") \
        .eq("estoque", "S") \
        .execute()

    df = pd.DataFrame(resp.data)

    if df.empty:
        return pd.DataFrame(columns=["ID_UNICO", "Ult_Entrada", "Ult_Saida"])

    # --- Monta Mesclado = "Service 02" → igual ao backup ---
    df["Mesclado"] = df["empresa"].astype(str).str.strip() + " " + df["filial"].astype(str).str.strip()
    df["Produto"]  = df["produto"].astype(str).str.strip()

    # --- Merge com estoque_empresas para pegar Empresa / Filial legível ---
    df = df.merge(
        df_emp.rename(columns={"id": "Mesclado", "empresa_filial": "Empresa / Filial"}),
        on="Mesclado",
        how="left"
    )

    df["digitacao"] = pd.to_datetime(df["digitacao"], errors="coerce")
    df["ID_UNICO"]  = df["Empresa / Filial"] + "|" + df["Produto"]

    # --- Separa entrada e saída pelo campo tipo ---
    df["DtEnt"] = df["digitacao"].where(df["tipo"].str.upper() == "ENTRADA", pd.NaT)
    df["DtSai"] = df["digitacao"].where(df["tipo"].str.upper() == "SAIDA",   pd.NaT)

    return df.groupby("ID_UNICO", as_index=False).agg(
        Ult_Entrada=("DtEnt", "max"),
        Ult_Saida  =("DtSai", "max"),
    )
