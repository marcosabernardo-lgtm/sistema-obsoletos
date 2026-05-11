import pandas as pd
import numpy as np
import streamlit as st
import httpx
from supabase import create_client, ClientOptions


def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    http_client = httpx.Client(verify=False, timeout=120.0)
    return create_client(url, key, options=ClientOptions(httpx_client=http_client))


def buscar_tudo(sb, tabela, colunas="*"):
    LIMIT = 1000
    pagina = 0
    todos = []
    while True:
        resp = (
            sb.table(tabela)
            .select(colunas)
            .range(pagina * LIMIT, (pagina + 1) * LIMIT - 1)
            .execute()
        )
        todos.extend(resp.data)
        if len(resp.data) < LIMIT:
            break
        pagina += 1
    return todos


def carregar_base_dio():
    sb = get_supabase()

    dados = buscar_tudo(
        sb, "dio_cache",
        "data_fechamento,empresa_filial,produto,descricao,saldo_atual,custo_total,vlr_unit,consumo_12m,consumo_diario,ult_mov_dio,dio"
    )

    df = pd.DataFrame(dados)

    df = df.rename(columns={
        "data_fechamento": "Data Fechamento",
        "empresa_filial":  "Empresa / Filial",
        "produto":         "Produto",
        "descricao":       "Descricao",
        "saldo_atual":     "Saldo Atual",
        "custo_total":     "Custo Total",
        "vlr_unit":        "Vlr Unit",
        "consumo_12m":     "Consumo_12m",
        "consumo_diario":  "Consumo_Diario",
        "ult_mov_dio":     "Ult_Mov_DIO",
        "dio":             "DIO",
    })

    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"])
    df["Ult_Mov_DIO"]     = pd.to_datetime(df["Ult_Mov_DIO"], errors="coerce")
    df["Saldo Atual"]     = pd.to_numeric(df["Saldo Atual"],    errors="coerce").fillna(0)
    df["Custo Total"]     = pd.to_numeric(df["Custo Total"],    errors="coerce").fillna(0)
    df["Vlr Unit"]        = pd.to_numeric(df["Vlr Unit"],       errors="coerce").fillna(0)
    df["Consumo_12m"]     = pd.to_numeric(df["Consumo_12m"],    errors="coerce").fillna(0)
    df["Consumo_Diario"]  = pd.to_numeric(df["Consumo_Diario"], errors="coerce").fillna(0)

    # NULL no Supabase (sem consumo) → np.inf para compatibilidade com dashboard
    dio_num = pd.to_numeric(df["DIO"], errors="coerce")
    df["DIO"] = np.where(dio_num.isna(), np.inf, dio_num)

    df["Produto"] = df["Produto"].astype(str).str.strip().str.replace(".0", "", regex=False)

    return df.sort_values("Data Fechamento").reset_index(drop=True)
