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
# HELPER: paginacao com filtro gte
# ==========================================================

def buscar_com_gte(sb, tabela, colunas, col_data, data_inicio):
    LIMIT = 1000
    offset = 0
    todos = []
    while True:
        resp = sb.table(tabela) \
            .select(colunas) \
            .gte(col_data, data_inicio) \
            .limit(LIMIT).offset(offset) \
            .execute()
        todos.extend(resp.data)
        if len(resp.data) < LIMIT:
            break
        offset += LIMIT
    return todos


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

    dados = buscar_com_gte(
        sb, "estoque_fechamentos",
        "data_fechamento, empresa, filial, tipo_de_estoque, conta, produto, descricao, unid, saldo_atual, vlr_unit, custo_total",
        "data_fechamento", "2025-12-31"
    )

    df = pd.DataFrame(dados)

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

    df["Empresa"]          = df["Empresa"].apply(normalizar_empresa)
    df["Filial"]           = df["Filial"].astype(str).str.strip().str.title()
    df["Empresa / Filial"] = df["Empresa"] + " / " + df["Filial"]
    df["Produto"]          = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)
    df["ID_UNICO"]         = df["Empresa / Filial"] + "|" + df["Produto"]
    df["Tipo de Estoque"]  = df["Tipo de Estoque"].fillna("Nao Informado").astype(str).str.strip().str.title()
    df["Conta"]            = df["Conta"].astype(str).str.strip().str.title()
    df["Vlr Unit"]         = pd.to_numeric(df["Vlr Unit"],    errors="coerce").fillna(0)
    df["Saldo Atual"]      = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"]      = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)

    # --- estoque_usadas: sobrescreve Conta ---
    resp_usadas = sb.table("estoque_usadas").select("codigo, tipo, empresa").execute()
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
# RESUMO MOVIMENTACOES (cache por data de fechamento)
# ==========================================================

def executar_resumo():
    sb = get_supabase()

    dados = buscar_com_gte(
        sb, "resumo_movimentacoes_cache",
        "data_fechamento, id_unico, ult_movimentacao, origem_mov",
        "data_fechamento", "2025-12-31"
    )

    df = pd.DataFrame(dados)

    if df.empty:
        return pd.DataFrame(columns=["Data Fechamento", "ID_UNICO", "Ult_Movimentacao", "Origem Mov"])

    df = df.rename(columns={
        "data_fechamento":  "Data Fechamento",
        "id_unico":         "ID_UNICO",
        "ult_movimentacao": "Ult_Movimentacao",
        "origem_mov":       "Origem Mov",
    })

    df["Ult_Movimentacao"] = pd.to_datetime(df["Ult_Movimentacao"], errors="coerce")

    return df


# ==========================================================
# MOTOR FINAL
# ==========================================================

def executar_motor():

    df_estoque = executar_estoque()
    df_resumo  = executar_resumo()

    # --- Merge por Data Fechamento + ID_UNICO ---
    df_estoque["Data Fechamento"] = pd.to_datetime(df_estoque["Data Fechamento"])
    df_resumo["Data Fechamento"]  = pd.to_datetime(df_resumo["Data Fechamento"])

    df_final = df_estoque.merge(df_resumo, on=["Data Fechamento", "ID_UNICO"], how="left")
    df_final = df_final.drop(columns=["ID_UNICO"])

    # --- Normalizacao ---
    df_final["Tipo de Estoque"] = df_final["Tipo de Estoque"].astype(str).str.title()

    CONTA_CORRECOES = {
        "MR":                  "Material Revenda",
        "MATERIAL REVENDA":    "Material Revenda",
        "MATERIAL DE REVENDA": "Material De Revenda",
    }
    df_final["Conta"] = df_final["Conta"].astype(str).str.strip().str.upper().map(
        lambda x: CONTA_CORRECOES.get(x, x)
    ).str.title()

    # --- Calculos por fechamento ---
    def calcular_por_fechamento(df):
        DataBase = pd.to_datetime(df["Data Fechamento"].iloc[0])

        df["Dias Sem Mov"] = (DataBase - df["Ult_Movimentacao"]).dt.days.fillna(9999)

        df["Meses Ult Mov"] = np.where(
            df["Ult_Movimentacao"].notna(),
            (DataBase.year  - df["Ult_Movimentacao"].dt.year)  * 12 +
            (DataBase.month - df["Ult_Movimentacao"].dt.month),
            np.nan
        )

        df["Status Estoque"] = np.where(
            df["Tipo de Estoque"].str.contains("Fabric", case=False),
            "Até 6 meses",
            np.where(
                df["Ult_Movimentacao"].isna() | (df["Meses Ult Mov"] > 6),
                "Obsoleto",
                "Até 6 meses"
            )
        )

        def status_mov(row):
            if "Fabric" in str(row["Tipo de Estoque"]):
                return "Até 6 meses"
            if pd.isna(row["Meses Ult Mov"]):
                return "Sem Movimento"
            if row["Meses Ult Mov"] <= 6:
                return "Até 6 meses"
            if row["Meses Ult Mov"] <= 12:
                return "Até 1 ano"
            if row["Meses Ult Mov"] <= 24:
                return "Até 2 anos"
            return "+ 2 anos"

        df["Status do Movimento"] = df.apply(status_mov, axis=1)

        def formatar(row):
            if "Fabric" in str(row["Tipo de Estoque"]):
                return "Em fabricacao"
            if pd.isna(row["Ult_Movimentacao"]):
                return "Sem movimento"
            dias      = (DataBase - row["Ult_Movimentacao"]).days
            anos      = dias // 365
            meses     = (dias % 365) // 30
            dias_rest = (dias % 365) % 30
            return f"{anos} anos {meses} meses {dias_rest} dias"

        df["Ano Meses Dias"] = df.apply(formatar, axis=1)

        return df

    df_final = df_final.groupby("Data Fechamento", group_keys=False).apply(calcular_por_fechamento)

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    print(f"Motor concluido — {len(df_final)} registros")
    return df_final, buffer.getvalue()
