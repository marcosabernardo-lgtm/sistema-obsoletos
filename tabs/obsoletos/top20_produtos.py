import streamlit as st
import pandas as pd
from utils.utils import botao_download_excel


def card_mini(titulo, valor):
    st.markdown(
        f"""
        <div style="
            border:1px solid #EC6E21;
            border-radius:8px;
            padding:10px 14px;
            text-align:center;
            background-color:#005562;
        ">
            <div style="font-size:11px;color:#aaa">{titulo}</div>
            <div style="font-size:18px;font-weight:bold;color:white">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render(df_filtrado, moeda_br):

    ultima_data = df_filtrado["Data Fechamento"].max()

    base = df_filtrado[df_filtrado["Data Fechamento"] == ultima_data]

    top20 = (
        base
        .groupby(
            ["Empresa / Filial", "Conta", "Produto", "Descricao"],
            as_index=False
        )
        .agg(
            Quantidade=("Saldo Atual", "sum"),
            Custo_Total=("Custo Total", "sum")
        )
    )

    total_geral = top20["Custo_Total"].sum()

    top20["%"] = (top20["Custo_Total"] / total_geral) * 100

    top20 = (
        top20
        .sort_values("Custo_Total", ascending=False)
        .head(20)
    )

    top20.insert(0, "Ranking", range(1, len(top20) + 1))
    top20 = top20.rename(columns={"Custo_Total": "Custo Total"})

    # ---------- CARDS MINI ----------
    total_top20       = top20["Custo Total"].sum()
    itens_top20       = top20["Produto"].nunique()
    perc_top20        = (total_top20 / total_geral * 100) if total_geral > 0 else 0
    ticket_medio_top20 = total_top20 / itens_top20 if itens_top20 > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: card_mini("Valor Top 20", moeda_br(total_top20))
    with c2: card_mini("Itens", f"{itens_top20}")
    with c3: card_mini("% do Obsoleto Total", f"{perc_top20:.2f}%")
    with c4: card_mini("Ticket Médio", moeda_br(ticket_medio_top20))

    st.markdown("")

    # ---------- DATAFRAME PARA EXPORTAR ----------
    export_df = top20.copy()

    # ---------- FORMATAÇÃO PARA TELA ----------
    top20["Custo Total"] = top20["Custo Total"].apply(moeda_br)
    top20["%"] = top20["%"].apply(lambda x: f"{x:.2f}%")

    top20 = top20[[
        "Ranking", "Empresa / Filial", "Conta", "Produto",
        "Descricao", "Quantidade", "Custo Total", "%"
    ]]

    # ---------- BOTÃO EXPORTAR ----------
    botao_download_excel(export_df, "top20_estoque_obsoleto.xlsx")

    # ---------- TABELA ----------
    st.dataframe(top20, use_container_width=True, hide_index=True)