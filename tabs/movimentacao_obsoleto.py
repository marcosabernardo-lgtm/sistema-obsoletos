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

    entrou = base[
        (base["obsoleto_atual"] == True) &
        (base["obsoleto_ant"] == False)
    ].copy()

    saiu = base[
        (base["obsoleto_atual"] == False) &
        (base["obsoleto_ant"] == True)
    ].copy()

    # -----------------------------
    # COLUNAS DISPONÍVEIS
    # -----------------------------

    colunas_base = [
        "Empresa / Filial",
        "Produto",
        "Descricao",
        "Ano Meses Dias",
        "Custo Total"
    ]

    colunas_existentes = [
        c for c in colunas_base if c in base.columns
    ]

    # -----------------------------
    # ENTRARAM NO OBSOLETO
    # -----------------------------

    st.subheader("Itens que Entraram no Obsoleto")

    if entrou.empty:
        st.info("Nenhum item entrou no obsoleto.")
    else:

        tabela = entrou[colunas_existentes].copy()

        if "Custo Total" in tabela.columns:
            tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)
            tabela = tabela.sort_values("Custo Total", ascending=False)

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    # -----------------------------
    # SAÍRAM DO OBSOLETO
    # -----------------------------

    st.subheader("Itens que Saíram do Obsoleto")

    if saiu.empty:
        st.info("Nenhum item saiu do obsoleto.")
    else:

        tabela = saiu[colunas_existentes].copy()

        if "Custo Total" in tabela.columns:
            tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)
            tabela = tabela.sort_values("Custo Total", ascending=False)

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True
        )
