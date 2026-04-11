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
# HELPER: paginacao
# ==========================================================

def buscar_tudo(sb, tabela, colunas):
    LIMIT = 1000
    offset = 0
    todos = []
    while True:
        resp = sb.table(tabela) \
            .select(colunas) \
            .limit(LIMIT).offset(offset) \
            .execute()
        todos.extend(resp.data)
        if len(resp.data) < LIMIT:
            break
        offset += LIMIT
    return todos


# ==========================================================
# MOTOR FINAL
# ==========================================================

def executar_motor():
    sb = get_supabase()

    # --- Busca tabela materializada (17496 linhas, ~18 chamadas) ---
    dados = buscar_tudo(
        sb, "motor_obsoletos_cache",
        "data_fechamento, empresa_filial, tipo_de_estoque, conta, produto, descricao, unid, saldo_atual, vlr_unit, custo_total, ult_movimentacao, origem_mov"
    )

    df = pd.DataFrame(dados)

    # --- Renomeia ---
    df = df.rename(columns={
        "data_fechamento":  "Data Fechamento",
        "empresa_filial":   "Empresa / Filial",
        "tipo_de_estoque":  "Tipo de Estoque",
        "conta":            "Conta",
        "produto":          "Produto",
        "descricao":        "Descricao",
        "unid":             "Unid",
        "saldo_atual":      "Saldo Atual",
        "vlr_unit":         "Vlr Unit",
        "custo_total":      "Custo Total",
        "ult_movimentacao": "Ult_Movimentacao",
        "origem_mov":       "Origem Mov",
    })

    # --- Tipos ---
    df["Data Fechamento"]  = pd.to_datetime(df["Data Fechamento"])
    df["Ult_Movimentacao"] = pd.to_datetime(df["Ult_Movimentacao"], errors="coerce")
    df["Vlr Unit"]         = pd.to_numeric(df["Vlr Unit"],    errors="coerce").fillna(0)
    df["Saldo Atual"]      = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"]      = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)
    df["Produto"]          = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)

    # --- Normalizacao ---
    df["Tipo de Estoque"] = df["Tipo de Estoque"].fillna("Nao Informado").astype(str).str.strip().str.title()

    CONTA_CORRECOES = {
        "MR":                  "Material Revenda",
        "MATERIAL REVENDA":    "Material Revenda",
        "MATERIAL DE REVENDA": "Material De Revenda",
    }
    df["Conta"] = df["Conta"].astype(str).str.strip().str.upper().map(
        lambda x: CONTA_CORRECOES.get(x, x)
    ).str.title()

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

    # --- Calculos por fechamento ---
    def calcular(grp):
        DataBase = grp.name

        grp["Dias Sem Mov"] = (DataBase - grp["Ult_Movimentacao"]).dt.days.fillna(9999)

        grp["Meses Ult Mov"] = np.where(
            grp["Ult_Movimentacao"].notna(),
            (DataBase.year  - grp["Ult_Movimentacao"].dt.year)  * 12 +
            (DataBase.month - grp["Ult_Movimentacao"].dt.month),
            np.nan
        )

        grp["Status Estoque"] = np.where(
            grp["Tipo de Estoque"].str.contains("Fabric", case=False),
            "Até 6 meses",
            np.where(
                grp["Ult_Movimentacao"].isna() | (grp["Meses Ult Mov"] > 6),
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

        grp["Status do Movimento"] = grp.apply(status_mov, axis=1)

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

        grp["Ano Meses Dias"] = grp.apply(formatar, axis=1)

        return grp

    df = df.groupby("Data Fechamento", group_keys=True).apply(calcular, include_groups=False).reset_index(level="Data Fechamento")

    df = df.sort_values("Data Fechamento").reset_index(drop=True)

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    print(f"Motor concluido — {len(df)} registros")
    return df, buffer.getvalue()
