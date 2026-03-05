import streamlit as st
import pandas as pd


def card(titulo, valor):

    st.markdown(
        f"""
        <div style="
            border:2px solid #ff6b00;
            border-radius:12px;
            padding:18px;
            text-align:center;
            margin-bottom:15px;
        ">
            <div style="font-size:16px">{titulo}</div>
            <div style="font-size:28px;font-weight:bold">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render(df_filtrado, moeda_br):

    datas = sorted(df_filtrado["Data Fechamento"].unique())

    if len(datas) < 2:
        st.warning("Histórico insuficiente para análise.")
        return

    data_atual = datas[-1]
    data_anterior = datas[-2]

    df_atual = df_filtrado[df_filtrado["Data Fechamento"] == data_atual].copy()
    df_ant = df_filtrado[df_filtrado["Data Fechamento"] == data_anterior].copy()

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

    # =================================================
    # ITENS QUE ENTRARAM
    # =================================================

    st.subheader("Itens que Entraram no Obsoleto")

    if not entrou.empty:

        qtd = len(entrou)
        valor = entrou["Custo Total"].sum()

        c1, c2 = st.columns(2)

        with c1:
            card("Qtd de Itens", f"{qtd:,}")

        with c2:
            card("Valor Total", moeda_br(valor))

        tabela = entrou[
            [
                "Empresa / Filial",
                "Produto",
                "Descricao",
                "Custo Total"
            ]
        ].copy()

        tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

        tabela = tabela.sort_values("Custo Total", ascending=False)

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("Nenhum item entrou no obsoleto.")

    st.markdown("---")

    # =================================================
    # ITENS QUE SAÍRAM
    # =================================================

    st.subheader("Itens que Saíram do Obsoleto")

    if not saiu.empty:

        qtd = len(saiu)
        valor = saiu["Custo Total"].sum()

        c1, c2 = st.columns(2)

        with c1:
            card("Qtd de Itens", f"{qtd:,}")

        with c2:
            card("Valor Total", moeda_br(valor))

        tabela = saiu[
            [
                "Empresa / Filial",
                "Produto",
                "Descricao",
                "Custo Total"
            ]
        ].copy()

        tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

        tabela = tabela.sort_values("Custo Total", ascending=False)

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("Nenhum item saiu do obsoleto.")
