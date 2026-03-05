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

def render(df_kpi, moeda_br):

    df = df_kpi.copy()

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

    # -------------------------------------------------
    # CARDS
    # -------------------------------------------------

    qtd_entrou = entrou["Produto"].nunique()
    valor_entrou = entrou["Custo Total"].sum()

    qtd_saiu = saiu["Produto"].nunique()
    valor_saiu = saiu["Custo Total"].sum()

    st.subheader("Movimentação do Obsoleto")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        card("Itens que Entraram", f"{qtd_entrou:,}")

    with c2:
        card("Valor que Entrou", moeda_br(valor_entrou))

    with c3:
        card("Itens que Saíram", f"{qtd_saiu:,}")

    with c4:
        card("Valor que Saiu", moeda_br(valor_saiu))

    st.markdown("---")

    # -------------------------------------------------
    # TABELA ÚNICA
    # -------------------------------------------------

    entrou["Status Mov"] = "🔴 Entrou"
    saiu["Status Mov"] = "🟢 Saiu"

    mov = pd.concat([entrou, saiu], ignore_index=True)

    if mov.empty:

        st.info("Nenhuma movimentação de obsoleto no período.")
        return

    tabela = mov[
        [
            "Status Mov",
            "Empresa / Filial",
            "Produto",
            "Descricao",
            "Saldo Atual",
            "Custo Total",
            "Ano Meses Dias"
        ]
    ].copy()

    tabela = tabela.rename(columns={
        "Saldo Atual": "Quantidade",
        "Ano Meses Dias": "Tempo sem Mov."
    })

    tabela = tabela.sort_values(
        "Custo Total",
        ascending=False
    )

    tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True
    )
