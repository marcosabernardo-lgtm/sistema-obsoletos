import streamlit as st
import pandas as pd


# -------------------------------------------------------
# CARD PADRÃO
# -------------------------------------------------------
def card(titulo, valor):

    st.markdown(
        f"""
        <div style="
            border:2px solid #EC6E21;
            border-radius:12px;
            padding:16px;
            height:90px;
            display:flex;
            flex-direction:column;
            justify-content:center;
            text-align:center;
        ">
            <div style="font-size:15px">{titulo}</div>
            <div style="font-size:28px;font-weight:bold">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# -------------------------------------------------------
# FUNÇÃO PRINCIPAL
# -------------------------------------------------------
def render(df_filtrado, moeda_br):

    df = df_filtrado.copy()

    datas = sorted(df["Data Fechamento"].unique())

    if len(datas) < 2:
        st.warning("Histórico insuficiente para análise.")
        return

    data_atual = datas[-1]
    data_anterior = datas[-2]

    df_atual = df[df["Data Fechamento"] == data_atual].copy()
    df_ant = df[df["Data Fechamento"] == data_anterior].copy()

    df_atual["obsoleto"] = df_atual["Status do Movimento"] != "Até 6 meses"
    df_ant["obsoleto"] = df_ant["Status do Movimento"] != "Até 6 meses"

    chave = [
        "Empresa / Filial",
        "Produto"
    ]

    base = df_atual.merge(
        df_ant[chave + ["obsoleto"]],
        on=chave,
        how="left",
        suffixes=("_atual", "_ant")
    )

    base["obsoleto_ant"] = base["obsoleto_ant"].fillna(False)

    entrou = base[
        (base["obsoleto_atual"] == True)
        &
        (base["obsoleto_ant"] == False)
    ].copy()

    saiu = base[
        (base["obsoleto_atual"] == False)
        &
        (base["obsoleto_ant"] == True)
    ].copy()

    # =====================================================
    # ITENS QUE ENTRARAM
    # =====================================================

    st.subheader("Itens que Entraram no Obsoleto")

    if not entrou.empty:

        qtd_itens = entrou["Produto"].nunique()
        valor_total = entrou["Custo Total"].sum()

        c1, c2, c3 = st.columns([1,1,2])

        with c1:
            card("Qtd de Itens", f"{qtd_itens:,}")

        with c2:
            card("Valor Total", moeda_br(valor_total))

        tabela = entrou[
            [
                "Empresa / Filial",
                "Produto",
                "Descricao",
                "Saldo Atual",
                "Custo Total"
            ]
        ].copy()

        tabela = tabela.sort_values(
            "Custo Total",
            ascending=False
        )

        tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

        tabela = tabela.rename(columns={
            "Saldo Atual": "Quantidade"
        })

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("Nenhum item entrou no obsoleto.")

    st.markdown("---")

    # =====================================================
    # ITENS QUE SAÍRAM
    # =====================================================

    st.subheader("Itens que Saíram do Obsoleto")

    if not saiu.empty:

        qtd_itens = saiu["Produto"].nunique()
        valor_total = saiu["Custo Total"].sum()

        c1, c2, c3 = st.columns([1,1,2])

        with c1:
            card("Qtd de Itens", f"{qtd_itens:,}")

        with c2:
            card("Valor Total", moeda_br(valor_total))

        tabela = saiu[
            [
                "Empresa / Filial",
                "Produto",
                "Descricao",
                "Saldo Atual",
                "Custo Total"
            ]
        ].copy()

        tabela = tabela.sort_values(
            "Custo Total",
            ascending=False
        )

        tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

        tabela = tabela.rename(columns={
            "Saldo Atual": "Quantidade"
        })

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("Nenhum item saiu do obsoleto.")
