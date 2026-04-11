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
# Substitui: executar_estoque(caminho_zip)
#   - ZIP lia 02_Estoque_Atual (sheet "Detalhado") → filtrando apenas o último fechamento
#   - ZIP lia 06_Usadas/*.xlsx por empresa → para sobrescrever a Conta com o tipo da usada
# Supabase:
#   - estoque_fechamentos → equivale ao 02_Estoque_Atual, já tem data_fechamento
#   - estoque_usadas      → equivale ao 06_Usadas, tem codigo, tipo, empresa
# ==========================================================

def executar_estoque():
    sb = get_supabase()

    # --- Pega a data do último fechamento ---
    resp_data = sb.table("estoque_fechamentos") \
        .select("data_fechamento") \
        .order("data_fechamento", desc=True) \
        .limit(1) \
        .execute()

    if not resp_data.data:
        raise Exception("Nenhum fechamento encontrado em estoque_fechamentos")

    ultima_data = resp_data.data[0]["data_fechamento"]

    # --- Carrega apenas o último fechamento ---
    resp = sb.table("estoque_fechamentos") \
        .select("data_fechamento, empresa, filial, tipo_de_estoque, conta, produto, descricao, unid, saldo_atual, vlr_unit, custo_total") \
        .eq("data_fechamento", ultima_data) \
        .execute()

    df = pd.DataFrame(resp.data)

    # --- Renomeia para os mesmos nomes do backup ---
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

    # --- Normaliza empresa (igual ao backup: vem bruto do Protheus) ---
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

    df["Empresa"] = df["Empresa"].apply(normalizar_empresa)
    df["Filial"]  = df["Filial"].astype(str).str.title()
    df["Empresa / Filial"] = df["Empresa"] + " / " + df["Filial"]
    df["Produto"] = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)
    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]

    # --- Tipo de Estoque ---
    if "Tipo de Estoque" in df.columns:
        df["Tipo de Estoque"] = df["Tipo de Estoque"].fillna("Não Informado").astype(str).str.strip().str.title()
    else:
        df["Tipo de Estoque"] = "Em Estoque"

    # --- Normaliza Conta ---
    if "Conta" in df.columns:
        df["Conta"] = df["Conta"].astype(str).str.strip().str.title()

    # --- Numéricos ---
    df["Vlr Unit"]    = pd.to_numeric(df["Vlr Unit"],    errors="coerce").fillna(0)
    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)

    # --- Carrega estoque_usadas e sobrescreve Conta (igual ao backup com 06_Usadas) ---
    # No backup: para cada empresa, se o produto estava no arquivo de usadas,
    # a Conta era substituída pelo Tipo da usada.
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

    colunas   = df.columns.tolist()
    nova_ordem = ["Data Fechamento", "Empresa / Filial"]
    demais    = [c for c in colunas if c not in nova_ordem]

    return df[nova_ordem + demais]


# ==========================================================
# MOVIMENTAÇÕES
# ==========================================================
# Substitui: executar_movimentacoes(caminho_zip)
#   - ZIP lia 04_Movimento/*.xlsx (Robotica e Service apenas)
#   - Usava 05_Empresas para montar "Empresa / Filial" via "Empresa Filial" (ex: "Robotica 00")
# Supabase:
#   - movimentos → empresa e filial já normalizados (ex: "Robotica", "00")
#   - Monta "Empresa / Filial" direto: empresa.title() + " / " + filial.title()
# ==========================================================

def executar_movimentacoes():
    sb = get_supabase()

    resp = sb.table("movimentos") \
        .select("empresa, filial, produto, dt_emissao") \
        .execute()

    df = pd.DataFrame(resp.data)

    if df.empty:
        return pd.DataFrame(columns=["ID_UNICO", "Ult_Mov"])

    # --- Monta Empresa / Filial no mesmo formato do estoque ---
    # movimentos.empresa já vem normalizado (ex: "Robotica", "Tools")
    # movimentos.filial  já vem normalizado (ex: "00", "01")
    # No backup, Filial vinha do Excel e era aplicado .str.title() → "00" → "00" (sem mudança)
    df["Empresa / Filial"] = df["empresa"].astype(str).str.strip() + " / " + df["filial"].astype(str).str.strip().str.title()
    df["Produto"]          = df["produto"].astype(str).str.strip()
    df["ID_UNICO"]         = df["Empresa / Filial"] + "|" + df["Produto"]
    df["DT Emissao"]       = pd.to_datetime(df["dt_emissao"], errors="coerce")

    df = df[df["DT Emissao"].notna()]

    return (
        df.groupby("ID_UNICO", as_index=False)["DT Emissao"]
        .max()
        .rename(columns={"DT Emissao": "Ult_Mov"})
    )


# ==========================================================
# ENTRADAS / SAÍDAS
# ==========================================================
# Substitui: executar_entradas_saidas(caminho_zip)
#   - ZIP lia 01_Entradas_Saidas/*.xlsx (abas ENTRADA e SAIDA, skiprows=1)
#   - Filtrava apenas linhas com ESTOQUE == "S"
#   - Usava 05_Empresas para montar "Empresa / Filial"
# Supabase:
#   - entradas_saidas → empresa e filial já normalizados
#   - Já deve conter apenas registros de estoque (filtro ESTOQUE=="S" foi feito na carga)
# ==========================================================

def executar_entradas_saidas():
    sb = get_supabase()

    resp = sb.table("entradas_saidas") \
        .select("empresa, filial, produto, dt_entrada, dt_saida") \
        .execute()

    df = pd.DataFrame(resp.data)

    if df.empty:
        return pd.DataFrame(columns=["ID_UNICO", "Ult_Entrada", "Ult_Saida"])

    # --- Monta Empresa / Filial igual ao estoque ---
    df["Empresa / Filial"] = df["empresa"].astype(str).str.strip() + " / " + df["filial"].astype(str).str.strip().str.title()
    df["Produto"]          = df["produto"].astype(str).str.strip()
    df["ID_UNICO"]         = df["Empresa / Filial"] + "|" + df["Produto"]

    df["DtEnt"] = pd.to_datetime(df["dt_entrada"], errors="coerce")
    df["DtSai"] = pd.to_datetime(df["dt_saida"],   errors="coerce")

    return df.groupby("ID_UNICO", as_index=False).agg(
        Ult_Entrada=("DtEnt", "max"),
        Ult_Saida  =("DtSai", "max"),
    )


# ==========================================================
# MOTOR FINAL
# ==========================================================
# Lógica idêntica ao backup — só muda a fonte dos dados.
# ==========================================================

def executar_motor():

    df_estoque = executar_estoque()
    df_mov     = executar_movimentacoes()
    df_es      = executar_entradas_saidas()

    df_final = df_estoque.merge(df_mov, on="ID_UNICO", how="left")
    df_final = df_final.merge(df_es,   on="ID_UNICO", how="left")

    # --- Última movimentação = max entre mov, entrada e saída ---
    df_final["Ult_Movimentacao"] = df_final[["Ult_Mov", "Ult_Entrada", "Ult_Saida"]].max(axis=1)
    df_final["Ult_Movimentacao"] = pd.to_datetime(df_final["Ult_Movimentacao"], errors="coerce")

    def origem(row):
        if row["Ult_Movimentacao"] == row["Ult_Saida"]:
            return "Ult_Saida"
        elif row["Ult_Movimentacao"] == row["Ult_Entrada"]:
            return "Ult_Entrada"
        elif row["Ult_Movimentacao"] == row["Ult_Mov"]:
            return "Ult_Mov"
        return None

    df_final["Origem Mov"] = df_final.apply(origem, axis=1)
    df_final = df_final.drop(columns=["Ult_Mov", "Ult_Entrada", "Ult_Saida"])

    # --- Normalização Title Case ---
    df_final["Tipo de Estoque"] = df_final["Tipo de Estoque"].astype(str).str.title()

    CONTA_CORRECOES = {
        "MR":                  "Material Revenda",
        "MATERIAL REVENDA":    "Material Revenda",
        "MATERIAL DE REVENDA": "Material De Revenda",
    }
    df_final["Conta"] = df_final["Conta"].astype(str).str.strip().str.upper().map(
        lambda x: CONTA_CORRECOES.get(x, x)
    ).str.title()

    df_final = df_final.drop(columns=["ID_UNICO"])

    # --- Data base = data do fechamento ---
    DataBase = pd.to_datetime(df_final["Data Fechamento"].iloc[0])

    df_final["Dias Sem Mov"] = (DataBase - df_final["Ult_Movimentacao"]).dt.days.fillna(9999)

    df_final["Meses Ult Mov"] = np.where(
        df_final["Ult_Movimentacao"].notna(),
        (DataBase.year  - df_final["Ult_Movimentacao"].dt.year)  * 12 +
        (DataBase.month - df_final["Ult_Movimentacao"].dt.month),
        np.nan
    )

    # --- Status Estoque (Obsoleto vs Ativo) ---
    df_final["Status Estoque"] = np.where(
        df_final["Tipo de Estoque"].str.contains("Fabric", case=False),
        "Até 6 meses",
        np.where(
            df_final["Ult_Movimentacao"].isna() | (df_final["Meses Ult Mov"] > 6),
            "Obsoleto",
            "Até 6 meses"
        )
    )

    # --- Status do Movimento (faixa de tempo) ---
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
            return "+ 1 ano"
        return "+ 2 anos"

    df_final["Status do Movimento"] = df_final.apply(status_mov, axis=1)

    # --- Formatação legível do tempo sem movimento ---
    def formatar(row):
        if "Fabric" in str(row["Tipo de Estoque"]):
            return "Em fabricação"
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

    print(f"✅ Motor concluído — {len(df_final)} registros")
    return df_final, buffer.getvalue()
