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
# FUNÇÃO GERADORA DE TEXTO (INTELIGÊNCIA DO BOTÃO)
# -------------------------------------------------------
def gerar_texto_analise(variacao_real, valor_entrou, valor_saiu, consumo, moeda_br):
    
    # 1. Analisa a tendência geral
    if variacao_real < 0:
        tendencia = "melhora"
        cor_titulo = "green"
        titulo = "✅ O Estoque Obsoleto REDUZIU neste mês"
    else:
        tendencia = "piora"
        cor_titulo = "red"
        titulo = "⚠️ O Estoque Obsoleto AUMENTOU neste mês"

    # 2. Analisa o Fluxo (Entrada vs Saída)
    saldo_mov = valor_entrou - valor_saiu
    if saldo_mov > 0:
        analise_fluxo = f"""
        **Ponto de Atenção Crítico:** A "torneira" de obsolescência está aberta. 
        O valor de novos itens obsoletos ({moeda_br(valor_entrou)}) superou o valor recuperado ({moeda_br(valor_saiu)}).
        Isso significa que, organicamente, o problema está crescendo.
        """
    else:
        analise_fluxo = f"""
        **Ponto Positivo:** O fluxo operacional está saudável. 
        Conseguimos recuperar/tirar da obsolescência ({moeda_br(valor_saiu)}) mais do que entrou de novos problemas ({moeda_br(valor_entrou)}).
        """

    # 3. Analisa o Consumo (O fiel da balança)
    if consumo < 0 and saldo_mov > 0:
        conclusao = f"""
        📉 **O que gerou a redução real?**
        Apesar da entrada alta de novos itens, o estoque total caiu exclusivamente devido ao **Consumo e Ajustes** expressivos de **{moeda_br(consumo)}**. 
        Basicamente, "baixamos" ou vendemos parcialmente itens que já eram velhos, o que mascarou a entrada de novos problemas.
        """
    elif consumo < 0:
        conclusao = f"""
        Além do fluxo, tivemos um apoio importante de **{moeda_br(consumo)}** em consumo/ajustes de itens antigos, acelerando a queda do estoque.
        """
    else:
        conclusao = f"""
        Houve um aumento de valor nos itens estocados (ajustes positivos) de {moeda_br(consumo)}, o que freou a redução do estoque.
        """

    return titulo, cor_titulo, analise_fluxo, conclusao

# -------------------------------------------------------
# FUNÇÃO PRINCIPAL
# -------------------------------------------------------
def render(df_hist, moeda_br):

    df = df_hist.copy()

    # --- PROCESSAMENTO DE DADOS (Mantido igual ao original) ---
    df = (
        df.groupby(
            ["Data Fechamento", "Empresa / Filial", "Produto", "Descricao", "Conta", "Status do Movimento"],
            as_index=False
        ).agg({"Saldo Atual": "sum", "Custo Total": "sum"})
    )

    df = (
        df.sort_values("Status do Movimento")
        .drop_duplicates(subset=["Data Fechamento", "Empresa / Filial", "Produto"], keep="first")
    )

    datas = sorted(df["Data Fechamento"].unique())

    if len(datas) < 2:
        st.warning("Histórico insuficiente.")
        return

    data_atual = datas[-1]
    data_anterior = datas[-2]

    df_atual = df[df["Data Fechamento"] == data_atual].copy()
    df_ant = df[df["Data Fechamento"] == data_anterior].copy()

    # Cálculos
    obs_ant = df_ant[df_ant["Status do Movimento"] != "Até 6 meses"]["Custo Total"].sum()
    obs_atual = df_atual[df_atual["Status do Movimento"] != "Até 6 meses"]["Custo Total"].sum()
    variacao_real = obs_atual - obs_ant

    df_atual["obsoleto"] = df_atual["Status do Movimento"] != "Até 6 meses"
    df_ant["obsoleto"] = df_ant["Status do Movimento"] != "Até 6 meses"

    chave = ["Empresa / Filial", "Produto"]
    base = df_atual.merge(df_ant[chave + ["obsoleto"]], on=chave, how="left", suffixes=("_atual", "_ant"))
    base["obsoleto_ant"] = base["obsoleto_ant"].fillna(False)

    entrou = base[(base["obsoleto_atual"] == True) & (base["obsoleto_ant"] == False)].copy()
    saiu = base[(base["obsoleto_atual"] == False) & (base["obsoleto_ant"] == True)].copy()

    qtd_entrou = entrou["Produto"].nunique()
    valor_entrou = entrou["Custo Total"].sum()
    qtd_saiu = saiu["Produto"].nunique()
    valor_saiu = saiu["Custo Total"].sum()
    saldo_mov = valor_entrou - valor_saiu
    consumo = variacao_real - saldo_mov

    # -------------------------------------------------------
    # VISUALIZAÇÃO (CARDS)
    # -------------------------------------------------------
    st.subheader("Movimentação do Obsoleto")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: card("Itens que Entraram", f"{qtd_entrou:,}")
    with c2: card("Valor que Entrou", moeda_br(valor_entrou))
    with c3: card("Valor que Saiu", moeda_br(valor_saiu))
    with c4: card("Saldo Movimentação", moeda_br(saldo_mov))
    with c5: card("Consumo / Ajustes", moeda_br(consumo))

    st.markdown("---")

    # -------------------------------------------------------
    # BOTÃO DE ANÁLISE (NOVA FUNCIONALIDADE)
    # -------------------------------------------------------
    col_btn, col_vazia = st.columns([1, 4])
    
    with col_btn:
        analisar = st.button("🤖 Analisar Cenário", type="primary", use_container_width=True)

    if analisar:
        titulo, cor, texto_fluxo, texto_conclusao = gerar_texto_analise(
            variacao_real, valor_entrou, valor_saiu, consumo, moeda_br
        )
        
        with st.container():
            st.markdown(f"<h3 style='color: {cor};'>{titulo}</h3>", unsafe_allow_html=True)
            st.info(f"{texto_fluxo}\n\n{texto_conclusao}")

    st.markdown("---")

    # -------------------------------------------------------
    # TABELA
    # -------------------------------------------------------
    entrou["Status Mov"] = "🔴 Entrou"
    saiu["Status Mov"] = "🟢 Saiu"
    mov = pd.concat([entrou, saiu])

    tabela = mov[[
        "Status Mov", "Empresa / Filial", "Produto", "Descricao", 
        "Saldo Atual", "Custo Total", "Status do Movimento"
    ]].copy()

    tabela = tabela.rename(columns={"Saldo Atual": "Quantidade", "Status do Movimento": "Status do Estoque"})
    tabela = tabela.sort_values("Custo Total", ascending=False)
    tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

    st.dataframe(tabela, use_container_width=True, hide_index=True)
