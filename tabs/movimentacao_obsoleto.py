import streamlit as st
import pandas as pd

# -------------------------------------------------------
# 1. FUNÇÃO DE ESTILO (CARD)
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
# 2. INTELIGÊNCIA DA ANÁLISE (GERADOR DE TEXTO)
# -------------------------------------------------------
def gerar_texto_analise(variacao_real, valor_entrou, valor_saiu, consumo, moeda_br):
    
    if variacao_real < 0:
        cor_titulo = "#28a745"  # Verde
        titulo = "✅ O Estoque Obsoleto REDUZIU neste mês"
    else:
        cor_titulo = "#dc3545"  # Vermelho
        titulo = "⚠️ O Estoque Obsoleto AUMENTOU neste mês"

    saldo_mov = valor_entrou - valor_saiu
    
    if saldo_mov > 0:
        texto_fluxo = f"""
        **⚠️ Ponto de Atenção Crítico (Fluxo):** 
        A "torneira" de obsolescência está aberta. O valor de novos itens obsoletos (**{moeda_br(valor_entrou)}**) superou o valor recuperado (**{moeda_br(valor_saiu)}**).
        Isso significa que, organicamente, o problema está crescendo.
        """
    else:
        texto_fluxo = f"""
        **✅ Ponto Positivo (Fluxo):** 
        O fluxo operacional está saudável. Conseguimos recuperar/tirar da obsolescência (**{moeda_br(valor_saiu)}**) mais do que entrou de novos problemas.
        """

    if consumo < 0:
        texto_conclusao = f"""
        **📉 O que impactou o resultado final?**
        O resultado foi fortemente impactado por **Consumo e Ajustes** (baixas contábeis, vendas parciais ou ajustes de inventário) no valor de **{moeda_br(consumo)}**.
        """
        if saldo_mov > 0 and variacao_real < 0:
            texto_conclusao += " Esse fator foi o único responsável por fazer o estoque total cair, compensando a alta entrada de novos itens."
    elif consumo > 0:
        texto_conclusao = f"""
        **📈 O que impactou o resultado final?**
        Houve ajustes positivos de valor ou inventário nos itens estocados (**+{moeda_br(consumo)}**), o que dificultou a redução do indicador geral.
        """
    else:
        texto_conclusao = "Não houve impacto relevante de ajustes ou consumo neste período."

    return titulo, cor_titulo, texto_fluxo, texto_conclusao

# -------------------------------------------------------
# 3. FUNÇÃO PRINCIPAL (RENDERIZAÇÃO DA TELA)
# -------------------------------------------------------
def render(df_hist, moeda_br):

    # --- CONTROLE DE ESTADO ---
    if "analise_visivel" not in st.session_state:
        st.session_state["analise_visivel"] = False

    def toggle_analise():
        st.session_state["analise_visivel"] = not st.session_state["analise_visivel"]

    # Recebe o DF já filtrado do arquivo principal
    df = df_hist.copy()

    # --- PROCESSAMENTO DE DADOS ---
    # Agrupa mantendo a coluna 'Conta'
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
        st.warning("Histórico insuficiente para análise com os filtros atuais.")
        return

    data_atual = datas[-1]
    data_anterior = datas[-2]

    df_atual = df[df["Data Fechamento"] == data_atual].copy()
    df_ant = df[df["Data Fechamento"] == data_anterior].copy()

    # --- CÁLCULOS ---
    obs_ant = df_ant[df_ant["Status do Movimento"] != "Até 6 meses"]["Custo Total"].sum()
    obs_atual = df_atual[df_atual["Status do Movimento"] != "Até 6 meses"]["Custo Total"].sum()
    variacao_real = obs_atual - obs_ant

    df_atual["obsoleto"] = df_atual["Status do Movimento"] != "Até 6 meses"
    df_ant["obsoleto"] = df_ant["Status do Movimento"] != "Até 6 meses"

    chave = ["Empresa / Filial", "Produto"]
    # Faz o merge para identificar entradas e saídas
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

    # --- VISUALIZAÇÃO ---
    st.subheader("Movimentação do Obsoleto")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: card("Itens que Entraram", f"{qtd_entrou:,}")
    with c2: card("Valor que Entrou", moeda_br(valor_entrou))
    with c3: card("Valor que Saiu", moeda_br(valor_saiu))
    with c4: card("Saldo Movimentação", moeda_br(saldo_mov))
    with c5: card("Consumo / Ajustes", moeda_br(consumo))

    st.markdown("---")

    # --- ÁREA DA ANÁLISE ---
    col_btn, col_vazia = st.columns([1, 4])
    
    if not st.session_state["analise_visivel"]:
        with col_btn:
            st.button("🤖 Analisar Cenário", type="primary", on_click=toggle_analise, use_container_width=True, key="btn_analisar_cenario")

    if st.session_state["analise_visivel"]:
        titulo, cor_titulo, texto_fluxo, texto_conclusao = gerar_texto_analise(
            variacao_real, valor_entrou, valor_saiu, consumo, moeda_br
        )
        
        st.markdown(f"""
        <div style="
            background-color: #1E1E1E; 
            padding: 20px; 
            border-radius: 10px; 
            border: 1px solid #444;
            margin-bottom: 15px;
        ">
            <h3 style="color: {cor_titulo}; margin-top: 0;">{titulo}</h3>
            <p style="color: #FFFFFF; font-size: 16px; line-height: 1.6;">{texto_fluxo}</p>
            <p style="color: #FFFFFF; font-size: 16px; line-height: 1.6;">{texto_conclusao}</p>
        </div>
        """, unsafe_allow_html=True)

        col_fechar, _ = st.columns([1, 4])
        with col_fechar:
            st.button("❌ Fechar Análise", on_click=toggle_analise, use_container_width=True, key="btn_fechar_analise")

    st.markdown("---")

    # --- TABELA ---
    entrou["Status Mov"] = "🔴 Entrou"
    saiu["Status Mov"] = "🟢 Saiu"
    mov = pd.concat([entrou, saiu])

    # AQUI FOI ADICIONADA A COLUNA 'Conta'
    tabela = mov[[
        "Status Mov", 
        "Empresa / Filial", 
        "Conta", 
        "Produto", 
        "Descricao", 
        "Saldo Atual", 
        "Custo Total", 
        "Status do Movimento"
    ]].copy()

    tabela = tabela.rename(columns={"Saldo Atual": "Quantidade", "Status do Movimento": "Status do Estoque"})
    tabela = tabela.sort_values("Custo Total", ascending=False)
    tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

    st.dataframe(tabela, use_container_width=True, hide_index=True)
