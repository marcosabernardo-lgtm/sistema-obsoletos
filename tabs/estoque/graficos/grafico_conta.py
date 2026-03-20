import streamlit as st
import pandas as pd


def render(df_hist, moeda_br, data_selecionada, valor_mom_total=None):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()
    datas_sorted = sorted(df_hist["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1

    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df_hist.columns)
        data_mom = None

    data_yoy_alvo = data_selecionada - pd.DateOffset(years=1)
    datas_yoy = [d for d in datas_sorted if abs((pd.Timestamp(d) - data_yoy_alvo).days) <= 31]
    if datas_yoy:
        data_yoy = min(datas_yoy, key=lambda d: abs((pd.Timestamp(d) - data_yoy_alvo).days))
        df_yoy = df_hist[df_hist["Data Fechamento"] == data_yoy].copy()
    else:
        df_yoy = pd.DataFrame(columns=df_hist.columns)
        data_yoy = None

    grp_atual = df_atual.groupby("Conta")["Custo Total"].sum().reset_index().rename(columns={"Custo Total": "Valor Estoque"})
    grp_mom   = df_mom.groupby("Conta")["Custo Total"].sum().reset_index().rename(columns={"Custo Total": "Valor MoM"}) if not df_mom.empty else pd.DataFrame(columns=["Conta", "Valor MoM"])
    grp_yoy   = df_yoy.groupby("Conta")["Custo Total"].sum().reset_index().rename(columns={"Custo Total": "Valor YoY"}) if not df_yoy.empty else pd.DataFrame(columns=["Conta", "Valor YoY"])

    df_tabela = grp_atual.merge(grp_mom, on="Conta", how="left")
    df_tabela = df_tabela.merge(grp_yoy, on="Conta", how="left")
    df_tabela["Valor MoM"] = df_tabela["Valor MoM"].fillna(0)
    df_tabela["Valor YoY"] = df_tabela["Valor YoY"].fillna(0)
    df_tabela["% MoM"] = df_tabela.apply(lambda r: ((r["Valor Estoque"] - r["Valor MoM"]) / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0, axis=1)
    df_tabela["% YoY"] = df_tabela.apply(lambda r: ((r["Valor Estoque"] - r["Valor YoY"]) / r["Valor YoY"] * 100) if r["Valor YoY"] != 0 else 0, axis=1)
    df_tabela = df_tabela.sort_values("Conta").reset_index(drop=True)

    atual_col = f"Valor Estoque {pd.Timestamp(data_selecionada).strftime('%y-%b').lower()}"
    mom_label = f"MoM {pd.Timestamp(data_mom).strftime('%y-%b').lower()}" if data_mom else "MoM"
    yoy_label = f"YoY {pd.Timestamp(data_yoy).strftime('%y-%b').lower()}" if data_yoy else "YoY"

    df_exib = df_tabela.rename(columns={
        "Valor Estoque": atual_col,
        "Valor MoM": mom_label,
        "Valor YoY": yoy_label,
    })

    total = pd.DataFrame([{
        "Conta": "Total",
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
        busca = st.text_input("🔍 PESQUISAR", placeholder="Conta, valor...", key="busca_conta")
    with col_ord:
        ord_col = st.selectbox("📊 Classificar por", list(df_exib.columns), key="ord_col_conta")
    with col_dir:
        ord_dir = st.selectbox("↕ Direção", ["⬇ Desc", "⬆ Asc"], key="ord_dir_conta")

    if busca:
        mask = df_exib.apply(lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
        df_exib = df_exib[mask]

    ascending = ord_dir == "⬆ Asc"
    try:
        df_exib = df_exib.sort_values(ord_col, ascending=ascending, key=lambda x: pd.to_numeric(x.astype(str).str.replace(r"[R$\s\.,%+]", "", regex=True).str.replace(",", "."), errors="coerce").fillna(x.astype(str)))
    except Exception:
        pass

    st.caption(f"{len(df_exib)} contas")
    st.dataframe(df_exib, use_container_width=True, hide_index=True)
