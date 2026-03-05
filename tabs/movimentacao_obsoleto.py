import streamlit as st
import pandas as pd


# -------------------------------------------------------
# CARD
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

def render(df_hist, moeda_br):

    df = df_hist.copy()

    # -------------------------------------------------------
    # CONSOLIDAR BASE
    # -------------------------------------------------------

    df = (
        df
        .groupby(
            [
                "Data Fechamento",
                "Empresa / Filial",
                "Produto",
                "Descricao",
                "Status do Movimento"
            ],
            as_index=False
        )
        .agg(
            {
                "Saldo Atual": "sum",
                "Custo Total": "sum"
            }
        )
    )

    datas = sorted(df["Data Fechamento"].unique())

    if len(datas) < 2:
        st.warning("Histórico insuficiente.")
        return

    data_atual = datas[-1]
    data_anterior = datas[-2]

    df_atual = df[df["Data Fechamento"] == data_atual].copy()
    df_ant = df[df["Data Fechamento"] == data_anterior].copy()

    # -------------------------------------------------------
    # CALCULAR OBSOLETO
    # -------------------------------------------------------

    obs_ant = df_ant[
        df_ant["Status do Movimento"] != "Até 6 meses"
    ]["Custo Total"].sum()

    obs_atual = df_atual[
        df_atual["Status do Movimento"] != "Até 6 meses"
    ]["Custo Total"].sum()

    variacao_real = obs_atual - obs_ant

    # -------------------------------------------------------
    # IDENTIFICAR ENTRADAS / SAÍDAS
    # -------------------------------------------------------

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
        (base["obsoleto_atual"] == True) &
        (base["obsoleto_ant"] == False)
    ].copy()

    saiu = base[
        (base["obsoleto_atual"] == False) &
        (base["obsoleto_ant"] == True)
    ].copy()

    # -------------------------------------------------------
    # VALORES
    # -------------------------------------------------------

    qtd_entrou = entrou["Produto"].nunique()
    valor_entrou = entrou["Custo Total"].sum()

    qtd_saiu = saiu["Produto"].nunique()
    valor_saiu = saiu["Custo Total"].sum()

    saldo_mov = valor_entrou - valor_saiu
    consumo = variacao_real - saldo_mov

    # -------------------------------------------------------
    # CARDS
    # -------------------------------------------------------

    st.subheader("Movimentação do Obsoleto")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        card("Itens que Entraram", f"{qtd_entrou:,}")

    with c2:
        card("Valor que Entrou", moeda_br(valor_entrou))

    with c3:
        card("Valor que Saiu", moeda_br(valor_saiu))

    with c4:
        card("Saldo Movimentação", moeda_br(saldo_mov))

    with c5:
        card("Consumo / Ajustes", moeda_br(consumo))

    st.markdown("---")

    # -------------------------------------------------------
    # TABELA
    # -------------------------------------------------------

    entrou["Status Mov"] = "🔴 Entrou"
    saiu["Status Mov"] = "🟢 Saiu"

    mov = pd.concat([entrou, saiu])

    tabela = mov[
        [
            "Status Mov",
            "Empresa / Filial",
            "Produto",
            "Descricao",
            "Saldo Atual",
            "Custo Total",
            "Status do Movimento"
        ]
    ].copy()

    tabela = tabela.rename(
        columns={
            "Saldo Atual": "Quantidade",
            "Status do Movimento": "Status do Estoque"
        }
    )

    tabela = tabela.sort_values("Custo Total", ascending=False)

    tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True
    )
