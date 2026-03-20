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

    for col in [atual_col, mom_label, yoy_label]:
        if col in df_exib.columns:
            df_exib[col] = df_exib[col].apply(moeda_br)
    for col in ["% MoM", "% YoY"]:
        if col in df_exib.columns:
            df_exib[col] = df_exib[col].apply(lambda v: f"{v:.1f}%")

    st.markdown("""
    <style>
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextInput"] > div,
    div[data-testid="stTextInput"] > div > div {
        background-color: #005562 !important;
    }
    div[data-testid="stTextInput"] input {
        border: 1px solid rgba(250,250,250,0.2) !important;
        border-radius: 6px !important;
        color: white !important;
        padding: 8px 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_busca, col_ord, col_dir = st.columns([3, 2, 1])
    with col_busca:
        busca = st.text_input("🔍 PESQUISAR", placeholder="Empresa, valor...", key="busca_empresa")
    with col_ord:
        ord_col = st.selectbox("📊 Classificar por", list(df_exib.columns), key="ord_col_empresa")
    with col_dir:
        ord_dir = st.selectbox("↕ Direção", ["⬇ Desc", "⬆ Asc"], key="ord_dir_empresa")

    # Separa linha total antes de filtrar/ordenar
    col_id = df_exib.columns[0]  # "Empresa / Filial"
    df_total = df_exib[df_exib[col_id] == "Total"].copy()
    df_exib  = df_exib[df_exib[col_id] != "Total"].copy()

    if busca:
        mask = df_exib.apply(lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
        df_exib = df_exib[mask]

    ascending = ord_dir == "⬆ Asc"
    try:
        df_exib = df_exib.sort_values(ord_col, ascending=ascending, key=lambda x: pd.to_numeric(x.astype(str).str.replace(r"[R$\s\.,%+]", "", regex=True).str.replace(",", "."), errors="coerce").fillna(x.astype(str)))
    except Exception:
        pass

    # Recoloca total sempre no final
    df_exib = pd.concat([df_exib, df_total], ignore_index=True)

    st.caption(f"{len(df_exib) - 1} empresas")
    st.dataframe(df_exib, use_container_width=True, hide_index=True)
