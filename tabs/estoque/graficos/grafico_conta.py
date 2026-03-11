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

    def formatar_perc(perc):
        if perc > 1:    return f"⬆ {abs(perc):.0f}%"
        elif perc < -1: return f"⬇ {abs(perc):.0f}%"
        else:           return f"● {abs(perc):.0f}%"

    # Montar linhas
    linhas = []
    for _, row in df_tabela.iterrows():
        linhas.append({
            "Conta":                 row["Conta"],
            "Valor Estoque (Total)": moeda_br(row["Valor Estoque"]),
            "Vir Est MoM":           moeda_br(row["Var MoM"]),
            "% MoM":                 formatar_perc(row["Perc MoM"]),
            "_perc":                 row["Perc MoM"],
        })
    linhas.append({
        "Conta":                 "Total",
        "Valor Estoque (Total)": moeda_br(total_atual),
        "Vir Est MoM":           moeda_br(total_var),
        "% MoM":                 formatar_perc(total_perc),
        "_perc":                 total_perc,
    })

    df_display = pd.DataFrame(linhas)

    # Guardar _perc antes de dropar
    percs = df_display["_perc"].tolist()
    df_display = df_display.drop(columns=["_perc"])

    # Styler
    def colorir_perc(row):
        perc   = percs[row.name] if row.name < len(percs) else 0
        styles = [""] * len(row)
        idx_p  = list(row.index).index("% MoM")
        if perc > 1:    styles[idx_p] = "color: #ff6b6b; font-weight: 600"
        elif perc < -1: styles[idx_p] = "color: #51cf66; font-weight: 600"
        else:           styles[idx_p] = "color: #f0a500; font-weight: 600"
        return styles

    def colorir_total(row):
        if row["Conta"] == "Total":
            return ["font-weight: 700; border-top: 2px solid #EC6E21"] * len(row)
        return [""] * len(row)

    styled = (
        df_display.style
        .apply(colorir_perc, axis=1)
        .apply(colorir_total, axis=1)
        .set_properties(**{
            "background-color": "#005562",
            "color": "white",
            "border": "1px solid #1a6e75",
            "padding": "8px 12px",
        })
        .set_table_styles([
            {"selector": "th", "props": [
                ("background-color", "#0f5a60"),
                ("color", "white"),
                ("font-weight", "700"),
                ("border-bottom", "2px solid #EC6E21"),
                ("padding", "10px 12px"),
            ]},
        ])
        .hide(axis="index")
    )

    st.dataframe(styled, use_container_width=True, height=500)