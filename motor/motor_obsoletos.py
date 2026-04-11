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
# HELPER: busca todos os registros com paginacao
# ==========================================================

def buscar_tudo(sb, tabela, colunas, filtros=None):
    """Pagina a query ate buscar todos os registros."""
    LIMIT = 1000
    offset = 0
    todos = []

    while True:
        query = sb.table(tabela).select(colunas).limit(LIMIT).offset(offset)
        if filtros:
            for col, val in filtros.items():
                query = query.eq(col, val)
        resp = query.execute()
        dados = resp.data
        todos.extend(dados)
        if len(dados) < LIMIT:
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

    # --- Ultimo fechamento ---
    resp_data = sb.table("estoque_fechamentos") \
        .select("data_fechamento") \
        .order("data_fechamento", desc=True) \
        .limit(1) \
        .execute()

    if not resp_data.data:
        raise Exception("Nenhum fechamento encontrado em estoque_fechamentos")

    ultima_data = resp_data.data[0]["data_fechamento"]

    # --- Carrega com paginacao ---
    dados = buscar_tudo(
        sb,
        "estoque_fechamentos",
        "data_fechamento, empresa, filial, tipo_de_estoque, conta, produto, descricao, unid, saldo_atual, vlr_unit, custo_total",
        {"data_fechamento": ultima_data}
    )

    df = pd.DataFrame(dados)

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

    # --- Normaliza empresa e filial ---
    df["Empresa"] = df["Empresa"].apply(normalizar_empresa)
    df["Filial"]  = df["Filial"].astype(str).str.strip().str.title()
    df["Empresa / Filial"] = df["Empresa"] + " / " + df["Filial"]
    df["Produto"]  = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)
    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]

    # --- Tipo de Estoque ---
    df["Tipo de Estoque"] = df["Tipo de Estoque"].fillna("Nao Informado").astype(str).str.strip().str.title()

    # --- Conta ---
    df["Conta"] = df["Conta"].astype(str).str.strip().str.title()

    # --- Numericos ---
    df["Vlr Unit"]    = pd.to_numeric(df["Vlr Unit"],    errors="coerce").fillna(0)
    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)

    # --- estoque_usadas: sobrescreve Conta com tipo da usada ---
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
# RESUMO MOVIMENTACOES (view no Supabase)
# ==========================================================

def executar_resumo():
    sb = get_supabase()

    dados = buscar_tudo(sb, "resumo_movimentacoes", "id_unico, ult_movimentacao")

    df = pd.DataFrame(dados)

    if df.empty:
        return pd.DataFrame(columns=["ID_UNICO", "Ult_Movimentacao"])

    df = df.rename(columns={
        "id_unico":         "ID_UNICO",
        "ult_movimentacao": "Ult_Movimentacao",
    })

    df["Ult_Movimentacao"] = pd.to_datetime(df["Ult_Movimentacao"], errors="coerce")

    return df


# ==========================================================
# MOTOR FINAL
# ==========================================================

def executar_motor():

    df_estoque = executar_estoque()
    df_resumo  = executar_resumo()

    # --- Merge estoque x resumo (left: itens sem mov ficam com NaT) ---
    df_final = df_estoque.merge(df_resumo, on="ID_UNICO", how="left")

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
        "Ate 6 meses",
        np.where(
            df_final["Ult_Movimentacao"].isna() | (df_final["Meses Ult Mov"] > 6),
            "Obsoleto",
            "Ate 6 meses"
        )
    )

    def status_mov(row):
        if "Fabric" in str(row["Tipo de Estoque"]):
            return "Ate 6 meses"
        if pd.isna(row["Meses Ult Mov"]):
            return "Sem Movimento"
        if row["Meses Ult Mov"] <= 6:
            return "Ate 6 meses"
        if row["Meses Ult Mov"] <= 12:
            return "Ate 1 ano"
        if row["Meses Ult Mov"] <= 24:
            return "+ 1 ano"
        return "+ 2 anos"

    df_final["Status do Movimento"] = df_final.apply(status_mov, axis=1)

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

    df_final["Ano Meses Dias"] = df_final.apply(formatar, axis=1)

    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)

    print(f"Motor concluido — {len(df_final)} registros")
    return df_final, buffer.getvalue()
