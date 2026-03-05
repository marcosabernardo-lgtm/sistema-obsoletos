import streamlit as st
import pandas as pd


def render(df_hist, moeda_br):

    datas = sorted(df_hist["Data Fechamento"].unique())

    if len(datas) < 2:
        st.warning("Histórico insuficiente para análise.")
        return

    data_atual = datas[-1]
    data_anterior = datas[-2]

    df_atual = df_hist[df_hist["Data Fechamento"] == data_atual].copy()
    df_ant = df_hist[df_hist["Data Fechamento"] == data_anterior].copy()

    df_atual["obsoleto"] = df_atual["Status do Movimento"] != "Até 6 meses"
    df_ant["obsoleto"] = df_ant["Status do Movimento"] != "Até 6 meses"

    chave = ["Empresa / Filial", "Produto"]

    base = df_atual.merge(
        df_ant[chave + ["obsoleto"]],
        on=chave,
        how="left",
        suffixes=("_atual", "_ant")
    )

    # -------------------------------------------------
    # ENTRARAM NO OBSOLETO
    # -------------------------------------------------

    entrou = base[
        (base["obsoleto_atual"] == True) &
        (base["obsoleto_ant"] == False)
    ]

    entrou = entrou.sort_values("Custo Total", ascending=False)

    # -------------------------------------------------
    # SAÍRAM DO OBSOLETO
    # -------------------------------------------------

    saiu = base[
        (base["obsoleto_atual"] == False) &
        (base["obsoleto_ant"] == True)
    ]

    saiu = saiu.sort_values("Custo Total", ascending=False)

    # -------------------------------------------------
    # TABELAS
    # -------------------------------------------------

    st.subheader("Itens que Entraram no Obsoleto")

    if entrou.empty:
        st.info("Nenhum item entrou no obsoleto.")
    else:
        tabela = entrou[[
            "Empresa / Filial",
            "Produto",
            "Descricao",
            "Custo Total"
        ]].copy()

        tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    st.subheader("Itens que Saíram do Obsoleto")

    if saiu.empty:
        st.info("Nenhum item saiu do obsoleto.")
    else:
        tabela = saiu[[
            "Empresa / Filial",
            "Produto",
            "Descricao",
            "Custo Total"
        ]].copy()

        tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True
        )
