import streamlit as st
import pandas as pd


def render(df_hist, moeda_br, data_selecionada, valor_mom_total=None):
    """
    Tabela 'Por Conta' replicando o visual do Power BI:
    Conta | Valor Estoque (Total) | Vir Est MoM | % MoM  com ícones coloridos.
    """

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    # ── Período atual ──────────────────────────────────────────────────────────
    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()

    # ── Período anterior (MoM) ─────────────────────────────────────────────────
    datas_sorted = sorted(df_hist["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1

    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df_hist.columns)

    # ── Agrupar por Conta ──────────────────────────────────────────────────────
    grp_atual = (
        df_atual.groupby("Conta")["Custo Total"]
        .sum()
        .reset_index()
        .rename(columns={"Custo Total": "Valor Estoque"})
    )

    grp_mom = (
        df_mom.groupby("Conta")["Custo Total"]
        .sum()
        .reset_index()
        .rename(columns={"Custo Total": "Valor MoM"})
    ) if not df_mom.empty else pd.DataFrame(columns=["Conta", "Valor MoM"])

    df_tabela = grp_atual.merge(grp_mom, on="Conta", how="left")
    df_tabela["Valor MoM"] = df_tabela["Valor MoM"].fillna(0)

    # Variação MoM = atual - anterior
    df_tabela["Var MoM"] = df_tabela["Valor Estoque"] - df_tabela["Valor MoM"]
    df_tabela["Perc MoM"] = df_tabela.apply(
        lambda r: (r["Var MoM"] / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0,
        axis=1
    )

    # Ordenar por Conta
    df_tabela = df_tabela.sort_values("Conta").reset_index(drop=True)

    # ── Totais ─────────────────────────────────────────────────────────────────
    total_atual = df_tabela["Valor Estoque"].sum()
    total_mom   = df_tabela["Valor MoM"].sum()
    total_var   = total_atual - total_mom
    total_perc  = (total_var / total_mom * 100) if total_mom != 0 else 0

    # ── Ícone e cor por % MoM ──────────────────────────────────────────────────
    def icone(perc):
        if perc > 1:
            return "⬆"
        elif perc < -1:
            return "⬇"
        else:
            return "●"

    def cor_linha(perc):
        """Retorna classe CSS baseada na variação."""
        if perc > 1:
            return "up"
        elif perc < -1:
            return "down"
        else:
            return "neutral"

    # ── Montar HTML da tabela ──────────────────────────────────────────────────
    st.markdown("""
    <style>
    .conta-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        color: white;
    }
    .conta-table th {
        background-color: #0f5a60;
        color: white;
        padding: 10px 14px;
        text-align: left;
        border-bottom: 2px solid #EC6E21;
        font-weight: 700;
    }
    .conta-table th:not(:first-child) { text-align: right; }
    .conta-table td {
        padding: 8px 14px;
        border-bottom: 1px solid #1a6e75;
        background-color: #005562;
    }
    .conta-table td:not(:first-child) { text-align: right; }
    .conta-table tr:hover td { background-color: #0a6570; }
    .conta-table .total-row td {
        background-color: #0f5a60;
        font-weight: 700;
        border-top: 2px solid #EC6E21;
    }
    .up      { color: #ff6b6b; }
    .down    { color: #51cf66; }
    .neutral { color: #f0a500; }
    </style>
    """, unsafe_allow_html=True)

    linhas_html = ""
    for _, row in df_tabela.iterrows():
        cls  = cor_linha(row["Perc MoM"])
        ico  = icone(row["Perc MoM"])
        perc = f"{abs(row['Perc MoM']):.0f}%"
        linhas_html += f"""
        <tr>
            <td>{row['Conta']}</td>
            <td>{moeda_br(row['Valor Estoque'])}</td>
            <td>{moeda_br(row['Var MoM'])}</td>
            <td><span class="{cls}">{ico} {perc}</span></td>
        </tr>"""

    # Linha de total
    cls_total  = cor_linha(total_perc)
    ico_total  = icone(total_perc)
    perc_total = f"{abs(total_perc):.0f}%"
    total_html = f"""
        <tr class="total-row">
            <td>Total</td>
            <td>{moeda_br(total_atual)}</td>
            <td>{moeda_br(total_var)}</td>
            <td><span class="{cls_total}">{ico_total} {perc_total}</span></td>
        </tr>"""

    tabela_html = f"""
    <table class="conta-table">
        <thead>
            <tr>
                <th>Conta</th>
                <th>Valor Estoque (Total)</th>
                <th>Vir Est MoM</th>
                <th>% MoM</th>
            </tr>
        </thead>
        <tbody>
            {linhas_html}
            {total_html}
        </tbody>
    </table>
    """

    st.markdown(tabela_html, unsafe_allow_html=True)