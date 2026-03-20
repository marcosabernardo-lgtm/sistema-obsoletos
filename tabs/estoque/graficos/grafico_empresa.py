import streamlit as st
import pandas as pd


def render(df, moeda_br, data_selecionada=None):
    df = df.copy()
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"])

    ultima_data = df["Data Fechamento"].max()
    data_ref = pd.Timestamp(data_selecionada) if data_selecionada is not None else ultima_data
    data_ref = pd.Timestamp(data_ref.date())
    df["Data Fechamento"] = df["Data Fechamento"].dt.normalize()

    df_atual = df[df["Data Fechamento"] == data_ref].copy()
    datas_sorted = sorted(df["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_ref) if data_ref in datas_sorted else -1

    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df[df["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df.columns)
        data_mom = None

    data_yoy_alvo = data_ref - pd.DateOffset(years=1)
    datas_yoy = [d for d in datas_sorted if abs((pd.Timestamp(d) - data_yoy_alvo).days) <= 31]
    if datas_yoy:
        data_yoy = min(datas_yoy, key=lambda d: abs((pd.Timestamp(d) - data_yoy_alvo).days))
        df_yoy = df[df["Data Fechamento"] == data_yoy].copy()
    else:
        df_yoy = pd.DataFrame(columns=df.columns)
        data_yoy = None

    grp_atual = df_atual.groupby("Empresa / Filial")["Custo Total"].sum().reset_index().rename(columns={"Custo Total": "Valor Estoque"})
    grp_mom   = df_mom.groupby("Empresa / Filial")["Custo Total"].sum().reset_index().rename(columns={"Custo Total": "Valor MoM"}) if not df_mom.empty else pd.DataFrame(columns=["Empresa / Filial", "Valor MoM"])
    grp_yoy   = df_yoy.groupby("Empresa / Filial")["Custo Total"].sum().reset_index().rename(columns={"Custo Total": "Valor YoY"}) if not df_yoy.empty else pd.DataFrame(columns=["Empresa / Filial", "Valor YoY"])

    df_tabela = grp_atual.merge(grp_mom, on="Empresa / Filial", how="left")
    df_tabela = df_tabela.merge(grp_yoy, on="Empresa / Filial", how="left")
    df_tabela["Valor MoM"] = df_tabela["Valor MoM"].fillna(0)
    df_tabela["Valor YoY"] = df_tabela["Valor YoY"].fillna(0)
    df_tabela["% MoM"] = df_tabela.apply(lambda r: ((r["Valor Estoque"] - r["Valor MoM"]) / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0, axis=1)
    df_tabela["% YoY"] = df_tabela.apply(lambda r: ((r["Valor Estoque"] - r["Valor YoY"]) / r["Valor YoY"] * 100) if r["Valor YoY"] != 0 else 0, axis=1)
    df_tabela = df_tabela.sort_values("Valor Estoque", ascending=False).reset_index(drop=True)

    atual_col = f"Valor Estoque {data_ref.strftime('%y-%b').lower()}"
    mom_label = f"MoM {pd.Timestamp(data_mom).strftime('%y-%b').lower()}" if data_mom else "MoM"
    yoy_label = f"YoY {pd.Timestamp(data_yoy).strftime('%y-%b').lower()}" if data_yoy else "YoY"

    df_exib = df_tabela.rename(columns={
        "Valor Estoque": atual_col,
        "Valor MoM": mom_label,
        "Valor YoY": yoy_label,
    })

    # Linha de total
    total = pd.DataFrame([{
        "Empresa / Filial": "Total",
        atual_col: df_tabela["Valor Estoque"].sum(),
        mom_label: df_tabela["Valor MoM"].sum(),
        "% MoM": ((df_tabela["Valor Estoque"].sum() - df_tabela["Valor MoM"].sum()) / df_tabela["Valor MoM"].sum() * 100) if df_tabela["Valor MoM"].sum() != 0 else 0,
        yoy_label: df_tabela["Valor YoY"].sum(),
        "% YoY": ((df_tabela["Valor Estoque"].sum() - df_tabela["Valor YoY"].sum()) / df_tabela["Valor YoY"].sum() * 100) if df_tabela["Valor YoY"].sum() != 0 else 0,
    }])

    df_exib = pd.concat([df_exib, total], ignore_index=True)

    st.dataframe(df_exib, use_container_width=True, hide_index=True)
