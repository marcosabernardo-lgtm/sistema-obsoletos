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

    # MoM
    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df[df["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df.columns)
        data_mom = None

    # YoY
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

    df_tabela["Perc MoM"] = df_tabela.apply(lambda r: ((r["Valor Estoque"] - r["Valor MoM"]) / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0, axis=1)
    df_tabela["Perc YoY"] = df_tabela.apply(lambda r: ((r["Valor Estoque"] - r["Valor YoY"]) / r["Valor YoY"] * 100) if r["Valor YoY"] != 0 else 0, axis=1)
    df_tabela = df_tabela.sort_values("Valor Estoque", ascending=False).reset_index(drop=True)

    total_atual    = df_tabela["Valor Estoque"].sum()
    total_mom      = df_tabela["Valor MoM"].sum()
    total_yoy      = df_tabela["Valor YoY"].sum()
    total_perc_mom = ((total_atual - total_mom) / total_mom * 100) if total_mom != 0 else 0
    total_perc_yoy = ((total_atual - total_yoy) / total_yoy * 100) if total_yoy != 0 else 0

    def icone_perc(perc):
        if perc > 1:    return f'<span style="color:#ff6b6b;font-weight:700">&#11014; {abs(perc):.0f}%</span>'
        elif perc < -1: return f'<span style="color:#51cf66;font-weight:700">&#11015; {abs(perc):.0f}%</span>'
        else:           return f'<span style="color:#f0a500;font-weight:700">&#9679; {abs(perc):.0f}%</span>'

    atual_label = data_ref.strftime('%d-%b').lower()
    mom_label   = f"MoM {pd.Timestamp(data_mom).strftime('%d-%b').lower()}" if data_mom else "MoM"
    yoy_label   = f"YoY {pd.Timestamp(data_yoy).strftime('%d-%b').lower()}" if data_yoy else "YoY"
    atual_col   = f"Valor Estoque {atual_label}"

    linhas = ""
    for _, row in df_tabela.iterrows():
        linhas += (
            "<tr>"
            f"<td>{row['Empresa / Filial']}</td>"
            f"<td>{moeda_br(row['Valor Estoque'])}</td>"
            f"<td>{moeda_br(row['Valor MoM'])}</td>"
            f"<td>{icone_perc(row['Perc MoM'])}</td>"
            f"<td>{moeda_br(row['Valor YoY']) if row['Valor YoY'] != 0 else '—'}</td>"
            f"<td>{icone_perc(row['Perc YoY']) if row['Valor YoY'] != 0 else '—'}</td>"
            "</tr>"
        )

    total_html = (
        "<tr style='font-weight:700;border-top:2px solid #EC6E21'>"
        f"<td>Total</td>"
        f"<td>{moeda_br(total_atual)}</td>"
        f"<td>{moeda_br(total_mom)}</td>"
        f"<td>{icone_perc(total_perc_mom)}</td>"
        f"<td>{moeda_br(total_yoy) if total_yoy != 0 else '—'}</td>"
        f"<td>{icone_perc(total_perc_yoy) if total_yoy != 0 else '—'}</td>"
        "</tr>"
    )

    css = (
        "<style>"
        ".tb-emp{width:100%;border-collapse:collapse;font-size:14px;color:white;}"
        ".tb-emp th{background-color:#0f5a60;color:white;padding:10px 14px;text-align:left;"
        "border-bottom:2px solid #EC6E21;font-weight:700;}"
        ".tb-emp th:not(:first-child){text-align:right;}"
        ".tb-emp td{padding:8px 14px;border-bottom:1px solid #1a6e75;background-color:#005562;color:white;}"
        ".tb-emp td:not(:first-child){text-align:right;}"
        ".tb-emp tr:hover td{background-color:#0a6570;}"
        "</style>"
    )

    tabela = (
        css
        + "<table class='tb-emp'><thead><tr>"
        + f"<th>Empresa / Filial</th><th>{atual_col}</th><th>{mom_label}</th><th>% MoM</th><th>{yoy_label}</th><th>% YoY</th>"
        + "</tr></thead><tbody>"
        + linhas + total_html
        + "</tbody></table>"
    )

    st.markdown(tabela, unsafe_allow_html=True)
