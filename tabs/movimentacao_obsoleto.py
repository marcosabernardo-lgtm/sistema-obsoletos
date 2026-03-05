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
    # CÁLCULOS
    # -------------------------------------------------

    qtd_entrou = entrou["Produto"].nunique()
    valor_entrou = entrou["Custo Total"].sum()

    qtd_saiu = saiu["Produto"].nunique()
    valor_saiu = saiu["Custo Total"].sum()

    saldo_mov = valor_entrou - valor_saiu

    obs_atual = df_atual[df_atual["obsoleto"]]["Custo Total"].sum()
    obs_ant = df_ant[df_ant["obsoleto"]]["Custo Total"].sum()

    variacao_real = obs_atual - obs_ant

    consumo = variacao_real - saldo_mov

    # -------------------------------------------------
    # CARDS
    # -------------------------------------------------

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

    # -------------------------------------------------
    # BOTÃO IA
    # -------------------------------------------------

    if st.button("🤖 Analisar movimentação do obsoleto"):

        st.markdown("### 📊 Interpretação automática")

        texto = []

        texto.append(
            f"No período analisado, **{moeda_br(valor_entrou)}** em itens entraram no obsoleto."
        )

        texto.append(
            f"Por outro lado, **{moeda_br(valor_saiu)}** deixaram de ser obsoletos."
        )

        if saldo_mov > 0:
            texto.append(
                f"O fluxo de deterioração foi **positivo em {moeda_br(saldo_mov)}**, indicando que mais itens se tornaram obsoletos do que voltaram a girar."
            )
        else:
            texto.append(
                f"O fluxo de deterioração foi **negativo em {moeda_br(abs(saldo_mov))}**, indicando recuperação do estoque."
            )

        if consumo < 0:
            texto.append(
                f"Além disso, houve **consumo ou baixa de {moeda_br(abs(consumo))}** em itens obsoletos."
            )
        else:
            texto.append(
                f"Houve **aumento de {moeda_br(consumo)}** devido a ajustes de estoque."
            )

        for t in texto:
            st.write("•", t)

        st.markdown("---")

        # -------------------------------------------------
        # RECONCILIAÇÃO DO ESTOQUE OBSOLETO
        # -------------------------------------------------

        st.markdown("### 🔎 Reconciliação do estoque obsoleto")

        resumo = """
Obsoleto anterior
+ Entraram no obsoleto
- Saíram do obsoleto
- Consumo / ajustes
----------------------------
Obsoleto atual
"""

        st.code(resumo)

        numeros = f"""
{moeda_br(obs_ant)}
+ {moeda_br(valor_entrou)}
- {moeda_br(valor_saiu)}
- {moeda_br(abs(consumo))}
----------------------------
{moeda_br(obs_atual)}
"""

        st.markdown("Aplicando seus números:")

        st.code(numeros)

        st.markdown("---")

    # -------------------------------------------------
    # TABELA DE MOVIMENTAÇÃO
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
            "Status do Movimento"
        ]
    ].copy()

    tabela = tabela.rename(columns={
        "Saldo Atual": "Quantidade",
        "Status do Movimento": "Status do Estoque"
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
