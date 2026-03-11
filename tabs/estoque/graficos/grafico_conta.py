import streamlit as st
import pandas as pd


def render(df_hist, moeda_br, data_selecionada, valor_mom_total=None):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    # Período atual
    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()

    # Período anterior (MoM)
    datas_sorted = sorted(df_hist["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1

    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df_hist.columns)

    # Agrupar por Conta
    grp_atual = (
        df_atual.groupby("Conta")["Custo Total"]
        .sum().reset_index()
        .rename(columns={"Custo Total": "Valor Estoque"})
    )

    grp_mom = (
        df_mom.groupby("Conta")["Custo Total"]
        .sum().reset_index()
        .rename(columns={"Custo Total": "Valor MoM"})
    ) if not df_mom.empty else pd.DataFrame(columns=["Conta", "Valor MoM"])

    df_tabela = grp_atual.merge(grp_mom, on="Conta", how="left")
    df_tabela["Valor MoM"] = df_tabela["Valor MoM"].fillna(0)
    df_tabela["Var MoM"]   = df_tabela["Valor Estoque"] - df_tabela["Valor MoM"]
    df_tabela["Perc MoM"]  = df_tabela.apply(
        lambda r: (r["Var MoM"] / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0, axis=1
    )
    df_tabela = df_tabela.sort_values("Conta").reset_index(drop=True)

    # Totais
    total_atual = df_tabela["Valor Estoque"].sum()
    total_mom   = df_tabela["Valor MoM"].sum()
    total_var   = total_atual - total_mom
    total_perc  = (total_var / total_mom * 100) if total_mom != 0 else 0

    # Helpers
    def cor_valor(v):
        return "color:#ff6b6b" if v < 0 else "color:white"

    def icone_perc(perc):
        if perc > 1:
            return '<span style="color:#51cf66;font-weight:700">&#11014; ' + f'{abs(perc):.0f}%</span>'
        elif perc < -1:
            return '<span style="color:#ff6b6b;font-weight:700">&#11015; ' + f'{abs(perc):.0f}%</span>'
        else:
            return '<span style="color:#f0a500;font-weight:700">&#9679; ' + f'{abs(perc):.0f}%</span>'

    # Montar linhas HTML
    linhas_html = ""
    for _, row in df_tabela.iterrows():
        cv = cor_valor(row["Var MoM"])
        linhas_html += (
            "<tr>"
            "<td>" + str(row['Conta']) + "</td>"
            "<td>" + moeda_br(row['Valor Estoque']) + "</td>"
            "<td style='" + cv + "'>" + moeda_br(row['Var MoM']) + "</td>"
            "<td>" + icone_perc(row['Perc MoM']) + "</td>"
            "</tr>"
        )

    cv_total = cor_valor(total_var)
    total_html = (
        "<tr style='font-weight:700;border-top:2px solid #EC6E21'>"
        "<td>Total</td>"
        "<td>" + moeda_br(total_atual) + "</td>"
        "<td style='" + cv_total + "'>" + moeda_br(total_var) + "</td>"
        "<td>" + icone_perc(total_perc) + "</td>"
        "</tr>"
    )

    css = (
        "<style>"
        ".tb-conta{width:100%;border-collapse:collapse;font-size:14px;color:white;}"
        ".tb-conta th{background-color:#0f5a60;color:white;padding:10px 14px;text-align:left;"
        "border-bottom:2px solid #EC6E21;font-weight:700;}"
        ".tb-conta th:not(:first-child){text-align:right;}"
        ".tb-conta td{padding:8px 14px;border-bottom:1px solid #1a6e75;"
        "background-color:#005562;color:white;}"
        ".tb-conta td:not(:first-child){text-align:right;}"
        ".tb-conta tr:hover td{background-color:#0a6570;}"
        "</style>"
    )

    tabela = (
        css
        + "<table class='tb-conta'>"
        + "<thead><tr>"
        + "<th>Conta</th>"
        + "<th>Valor Estoque (Total)</th>"
        + "<th>Vir Est MoM</th>"
        + "<th>% MoM</th>"
        + "</tr></thead>"
        + "<tbody>"
        + linhas_html
        + total_html
        + "</tbody></table>"
    )

    st.html(tabela)