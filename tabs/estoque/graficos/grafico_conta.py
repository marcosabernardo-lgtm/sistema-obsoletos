import streamlit as st
import pandas as pd


def render(df_hist, moeda_br, data_selecionada, valor_mom_total=None):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()

    datas_sorted = sorted(df_hist["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1

    # MoM
    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df_hist.columns)
        data_mom = None

    # YoY
    data_yoy_alvo = data_selecionada - pd.DateOffset(years=1)
    datas_yoy = [d for d in datas_sorted if abs((pd.Timestamp(d) - data_yoy_alvo).days) <= 31]
    if datas_yoy:
        data_yoy = min(datas_yoy, key=lambda d: abs((pd.Timestamp(d) - data_yoy_alvo).days))
        df_yoy = df_hist[df_hist["Data Fechamento"] == data_yoy].copy()
    else:
        df_yoy = pd.DataFrame(columns=df_hist.columns)
        data_yoy = None

    # Agrupamentos
    grp_atual = (
        df_atual.groupby("Conta")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Valor Estoque"})
    )
    grp_mom = (
        df_mom.groupby("Conta")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Valor MoM"})
    ) if not df_mom.empty else pd.DataFrame(columns=["Conta", "Valor MoM"])

    grp_yoy = (
        df_yoy.groupby("Conta")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Valor YoY"})
    ) if not df_yoy.empty else pd.DataFrame(columns=["Conta", "Valor YoY"])

    df_tabela = grp_atual.merge(grp_mom, on="Conta", how="left")
    df_tabela = df_tabela.merge(grp_yoy, on="Conta", how="left")
    df_tabela["Valor MoM"] = df_tabela["Valor MoM"].fillna(0)
    df_tabela["Valor YoY"] = df_tabela["Valor YoY"].fillna(0)

    df_tabela["Perc MoM"] = df_tabela.apply(
        lambda r: ((r["Valor Estoque"] - r["Valor MoM"]) / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0, axis=1
    )
    df_tabela["Perc YoY"] = df_tabela.apply(
        lambda r: ((r["Valor Estoque"] - r["Valor YoY"]) / r["Valor YoY"] * 100) if r["Valor YoY"] != 0 else 0, axis=1
    )

    df_tabela = df_tabela.sort_values("Conta").reset_index(drop=True)

    total_atual    = df_tabela["Valor Estoque"].sum()
    total_mom      = df_tabela["Valor MoM"].sum()
    total_yoy      = df_tabela["Valor YoY"].sum()
    total_perc_mom = ((total_atual - total_mom) / total_mom * 100) if total_mom != 0 else 0
    total_perc_yoy = ((total_atual - total_yoy) / total_yoy * 100) if total_yoy != 0 else 0

    def icone_perc(perc):
        if perc > 1:    return f'<span style="color:#ff6b6b;font-weight:700">&#11014; {abs(perc):.0f}%</span>'
        elif perc < -1: return f'<span style="color:#51cf66;font-weight:700">&#11015; {abs(perc):.0f}%</span>'
        else:           return f'<span style="color:#f0a500;font-weight:700">&#9679; {abs(perc):.0f}%</span>'

    mom_label = f"Vir Est MoM ({pd.Timestamp(data_mom).strftime('%y-%b').lower()})" if data_mom else "Vir Est MoM"
    yoy_label = f"Vir Est YoY ({pd.Timestamp(data_yoy).strftime('%y-%b').lower()})" if data_yoy else "Vir Est YoY"

    linhas_html = ""
    for _, row in df_tabela.iterrows():
        linhas_html += (
            "<tr>"
            f"<td>{row['Conta']}</td>"
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
        ".tb-conta{width:100%;border-collapse:collapse;font-size:14px;color:white;}"
        ".tb-conta th{background-color:#0f5a60;color:white;padding:10px 14px;text-align:left;"
        "border-bottom:2px solid #EC6E21;font-weight:700;}"
        ".tb-conta th:first-child{width:200px;min-width:200px;max-width:200px;}"
        ".tb-conta th:not(:first-child){text-align:right;}"
        ".tb-conta td{padding:8px 14px;border-bottom:1px solid #1a6e75;"
        "background-color:#005562;color:white;}"
        ".tb-conta td:first-child{width:200px;min-width:200px;max-width:200px;}"
        ".tb-conta td:not(:first-child){text-align:right;}"
        ".tb-conta tr:hover td{background-color:#0a6570;}"
        "</style>"
    )

    tabela = (
        css
        + "<table class='tb-conta'><thead><tr>"
        + f"<th>Conta</th><th>Valor Estoque (Total)</th><th>{mom_label}</th><th>% MoM</th><th>{yoy_label}</th><th>% YoY</th>"
        + "</tr></thead><tbody>"
        + linhas_html
        + total_html
        + "</tbody></table>"
    )

    st.html(tabela)
