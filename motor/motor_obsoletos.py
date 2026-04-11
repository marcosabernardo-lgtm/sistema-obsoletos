import pandas as pd
import io
import numpy as np
import streamlit as st
from supabase import create_client


def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


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
    resp_data = sb.table("estoque_fechamentos").select("data_fechamento").order("data_fechamento", desc=True).limit(1).execute()
    if not resp_data.data:
        raise Exception("Nenhum fechamento encontrado")
    ultima_data = resp_data.data[0]["data_fechamento"]
    resp = sb.table("estoque_fechamentos").select("data_fechamento, empresa, filial, tipo_de_estoque, conta, produto, descricao, unid, saldo_atual, vlr_unit, custo_total").eq("data_fechamento", ultima_data).execute()
    df = pd.DataFrame(resp.data)
    df = df.rename(columns={"data_fechamento":"Data Fechamento","empresa":"Empresa","filial":"Filial","tipo_de_estoque":"Tipo de Estoque","conta":"Conta","produto":"Produto","descricao":"Descricao","unid":"Unid","saldo_atual":"Saldo Atual","vlr_unit":"Vlr Unit","custo_total":"Custo Total"})
    df["Empresa"] = df["Empresa"].apply(normalizar_empresa)
    df["Filial"] = df["Filial"].astype(str).str.strip().str.title()
    df["Empresa / Filial"] = df["Empresa"] + " / " + df["Filial"]
    df["Produto"] = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)
    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]
    df["Tipo de Estoque"] = df["Tipo de Estoque"].fillna("Nao Informado").astype(str).str.strip().str.title()
    df["Conta"] = df["Conta"].astype(str).str.strip().str.title()
    df["Vlr Unit"] = pd.to_numeric(df["Vlr Unit"], errors="coerce").fillna(0)
    df["Saldo Atual"] = pd.to_numeric(df["Saldo Atual"], errors="coerce").fillna(0)
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)
    resp_usadas = sb.table("estoque_usadas").select("codigo, tipo, empresa").execute()
    df_usadas = pd.DataFrame(resp_usadas.data)
    if not df_usadas.empty:
        df_usadas["codigo"] = df_usadas["codigo"].astype(str).str.strip().str.replace(".0", "", regex=False)
        df_usadas["tipo"] = df_usadas["tipo"].astype(str).str.strip().str.title()
        df_usadas["empresa"] = df_usadas["empresa"].astype(str).str.strip()
        for _, row_u in df_usadas.iterrows():
            mask = (df["Empresa / Filial"].str.startswith(row_u["empresa"]) & (df["Produto"] == row_u["codigo"]))
            df.loc[mask, "Conta"] = row_u["tipo"]
    df = df.drop(columns=["Empresa", "Filial"])
    nova_ordem = ["Data Fechamento", "Empresa / Filial"]
    demais = [c for c in df.columns if c not in nova_ordem]
    return df[nova_ordem + demais]


def executar_movimentacoes():
    sb = get_supabase()
    resp_emp = sb.table("estoque_empresas").select("id, empresa_filial").execute()
    df_emp = pd.DataFrame(resp_emp.data)
    df_emp["id"] = df_emp["id"].astype(str).str.strip()
    df_emp["empresa_filial"] = df_emp["empresa_filial"].astype(str).str.strip()
    resp = sb.table("movimentos").select("empresa, filial, produto, dt_emissao").execute()
    df = pd.DataFrame(resp.data)
    if df.empty:
        return pd.DataFrame(columns=["ID_UNICO", "Ult_Mov"])
    df["Mesclado"] = df["empresa"].astype(str).str.strip() + " " + df["filial"].astype(str).str.strip()
    df["Produto"] = df["produto"].astype(str).str.strip()
    df = df.merge(df_emp.rename(columns={"id": "Mesclado", "empresa_filial": "Empresa / Filial"}), on="Mesclado", how="left")
    df["DT Emissao"] = pd.to_datetime(df["dt_emissao"], errors="coerce")
    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]
    df = df[df["DT Emissao"].notna()]
    return df.groupby("ID_UNICO", as_index=False)["DT Emissao"].max().rename(columns={"DT Emissao": "Ult_Mov"})


def executar_entradas_saidas():
    sb = get_supabase()
    resp_emp = sb.table("estoque_empresas").select("id, empresa_filial").execute()
    df_emp = pd.DataFrame(resp_emp.data)
    df_emp["id"] = df_emp["id"].astype(str).str.strip()
    df_emp["empresa_filial"] = df_emp["empresa_filial"].astype(str).str.strip()
    resp = sb.table("entradas_saidas").select("empresa, filial, produto, tipo, digitacao").eq("estoque", "S").execute()
    df = pd.DataFrame(resp.data)
    if df.empty:
        return pd.DataFrame(columns=["ID_UNICO", "Ult_Entrada", "Ult_Saida"])
    df["Mesclado"] = df["empresa"].astype(str).str.strip() + " " + df["filial"].astype(str).str.strip()
    df["Produto"] = df["produto"].astype(str).str.strip()
    df = df.merge(df_emp.rename(columns={"id": "Mesclado", "empresa_filial": "Empresa / Filial"}), on="Mesclado", how="left")
    df["digitacao"] = pd.to_datetime(df["digitacao"], errors="coerce")
    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]
    df["DtEnt"] = df["digitacao"].where(df["tipo"].str.upper() == "ENTRADA", pd.NaT)
    df["DtSai"] = df["digitacao"].where(df["tipo"].str.upper() == "SAIDA", pd.NaT)
    return df.groupby("ID_UNICO", as_index=False).agg(Ult_Entrada=("DtEnt", "max"), Ult_Saida=("DtSai", "max"))


def executar_motor():
    df_estoque = executar_estoque()
    df_mov = executar_movimentacoes()
    df_es = executar_entradas_saidas()
    df_final = df_estoque.merge(df_mov, on="ID_UNICO", how="left")
    df_final = df_final.merge(df_es, on="ID_UNICO", how="left")
    df_final["Ult_Movimentacao"] = df_final[["Ult_Mov", "Ult_Entrada", "Ult_Saida"]].max(axis=1)
    df_final["Ult_Movimentacao"] = pd.to_datetime(df_final["Ult_Movimentacao"], errors="coerce")
    def origem(row):
        if row["Ult_Movimentacao"] == row["Ult_Saida"]: return "Ult_Saida"
        elif row["Ult_Movimentacao"] == row["Ult_Entrada"]: return "Ult_Entrada"
        elif row["Ult_Movimentacao"] == row["Ult_Mov"]: return "Ult_Mov"
        return None
    df_final["Origem Mov"] = df_final.apply(origem, axis=1)
    df_final = df_final.drop(columns=["Ult_Mov", "Ult_Entrada", "Ult_Saida"])
    df_final["Tipo de Estoque"] = df_final["Tipo de Estoque"].astype(str).str.title()
    CONTA_CORRECOES = {"MR": "Material Revenda", "MATERIAL REVENDA": "Material Revenda", "MATERIAL DE REVENDA": "Material De Revenda"}
    df_final["Conta"] = df_final["Conta"].astype(str).str.strip().str.upper().map(lambda x: CONTA_CORRECOES.get(x, x)).str.title()
    df_final = df_final.drop(columns=["ID_UNICO"])
    DataBase = pd.to_datetime(df_final["Data Fechamento"].iloc[0])
    df_final["Dias Sem Mov"] = (DataBase - df_final["Ult_Movimentacao"]).dt.days.fillna(9999)
    df_final["Meses Ult Mov"] = np.where(df_final["Ult_Movimentacao"].notna(), (DataBase.year - df_final["Ult_Movimentacao"].dt.year) * 12 + (DataBase.month - df_final["Ult_Movimentacao"].dt.month), np.nan)
    df_final["Status Estoque"] = np.where(df_final["Tipo de Estoque"].str.contains("Fabric", case=False), "Ate 6 meses", np.where(df_final["Ult_Movimentacao"].isna() | (df_final["Meses Ult Mov"] > 6), "Obsoleto", "Ate 6 meses"))
    def status_mov(row):
        if "Fabric" in str(row["Tipo de Estoque"]): return "Ate 6 meses"
        if pd.isna(row["Meses Ult Mov"]): return "Sem Movimento"
        if row["Meses Ult Mov"] <= 6: return "Ate 6 meses"
        if row["Meses Ult Mov"] <= 12: return "Ate 1 ano"
        if row["Meses Ult Mov"] <= 24: return "+ 1 ano"
        return "+ 2 anos"
    df_final["Status do Movimento"] = df_final.apply(status_mov, axis=1)
    def formatar(row):
        if "Fabric" in str(row["Tipo de Estoque"]): return "Em fabricacao"
        if pd.isna(row["Ult_Movimentacao"]): return "Sem movimento"
        dias = (DataBase - row["Ult_Movimentacao"]).days
        anos = dias // 365
        meses = (dias % 365) // 30
        dias_rest = (dias % 365) % 30
        return f"{anos} anos {meses} meses {dias_rest} dias"
    df_final["Ano Meses Dias"] = df_final.apply(formatar, axis=1)
    buffer = io.BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)
    print(f"Motor concluido — {len(df_final)} registros")
    return df_final, buffer.getvalue()
