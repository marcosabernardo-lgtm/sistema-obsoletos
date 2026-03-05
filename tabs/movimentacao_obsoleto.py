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
    
    # A) Analisa se o estoque total subiu ou desceu
    if variacao_real < 0:
        # Estoque caiu (Bom)
        cor_titulo = "#28a745"  # Verde
        titulo = "✅ O Estoque Obsoleto REDUZIU neste mês"
    else:
        # Estoque subiu (Ruim)
        cor_titulo = "#dc3545"  # Vermelho
        titulo = "⚠️ O Estoque Obsoleto AUMENTOU neste mês"

    # B) Analisa o Fluxo (Entrada vs Saída)
    saldo_mov = valor_entrou - valor_saiu
    
    if saldo_mov > 0:
        # Entrou mais do que saiu (Ruim)
        texto_fluxo = f"""
        **⚠️ Ponto de Atenção Crítico (Fluxo):** 
        A "torneira" de obsolescência está aberta. O valor de novos itens obsoletos (**{moeda_br(valor_entrou)}**) superou o valor recuperado (**{moeda_br(valor_saiu)}**).
        Isso significa que, organicamente, o problema está crescendo.
        """
    else:
        # Saiu mais do que entrou (Bom)
        texto_fluxo = f"""
        **✅ Ponto Positivo (Fluxo):** 
        O fluxo operacional está saudável. Conseguimos recuperar/tirar da obsolescência (**{moeda_br(valor_saiu)}**) mais do que entrou de novos problemas.
        """

    # C) Analisa o Consumo / Ajustes (O fiel da balança)
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

    df = df_hist.copy()

    # --- PROCESSAMENTO DE DADOS ---
    # Agrupa por Produto + Status para garantir consistência
    df = (
        df
        .groupby(
            ["Data Fechamento", "Empresa / Filial", "Produto", "Descricao", "Conta", "Status do Movimento"],
            as_index=False
        )
        .agg({"Saldo Atual": "sum", "Custo Total": "sum"})
    )

    # Garante registro único
    df = (
        df
        .sort_values("Status do Movimento")
        .drop_duplicates(subset=["Data Fechamento", "Empresa / Filial", "Produto"], keep="first")
    )

    datas = sorted(df["Data Fechamento"].unique())

    if len(datas) < 2:
        st.warning("Histórico insuficiente para análise de movimentação.")
        return

    data_atual = datas[-1]
    data_anterior = datas[-2]

    df_atual = df[df["Data Fechamento"] == data_atual].copy()
    df_ant = df[df["Data Fechamento"] == data_anterior].copy()

    # --- CÁLCULOS ---
    
    # 1. Totais
    obs_ant = df_ant[df_ant["Status do Movimento"] != "Até 6 meses"]["Custo Total"].sum()
    obs_atual = df_atual[df_atual["Status do Movimento"] != "Até 6 meses"]["Custo Total"].sum()
    variacao_real = obs_atual - obs_ant

    # 2. Identificar Entradas e Saídas
    df_atual["obsoleto"] = df_atual["Status do Movimento"] != "Até 6 meses"
    df_ant["obsoleto"] = df_ant["Status do Movimento"] != "Até 6 meses"

    chave = ["Empresa / Filial", "Produto"]
    base = df_atual.merge(df_ant[chave + ["obsoleto"]], on=chave, how="left", suffixes=("_atual", "_ant"))
    base["obsoleto_ant"] = base["obsoleto_ant"].fillna(False)

    entrou = base[(base["obsoleto_atual"] == True) & (base["obsoleto_ant"] == False)].copy()
    saiu = base[(base["obsoleto_atual"] == False) & (base["obsoleto_ant"] == True)].copy()

    # 3. Valores Finais
    qtd_entrou = entrou["Produto"].nunique()
    valor_entrou = entrou["Custo Total"].sum()

    qtd_saiu = saiu["Produto"].nunique()
    valor_saiu = saiu["Custo Total"].sum()

    saldo_mov = valor_entrou - valor_saiu
    consumo = variacao_real - saldo_mov  # Conta de chegada

    # --- VISUALIZAÇÃO: CARDS ---
    
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

    # --- SEÇÃO DO BOTÃO DE ANÁLISE ---
    
    st.markdown("---")
    
    # Cria colunas para o botão não ficar esticado na tela toda
    col_btn, col_vazia = st.columns([1, 4])
    
    with col_btn:
        analisar = st.button("🤖 Analisar Cenário", type="primary", use_container_width=True, key="btn_analise_obs")

    # Lógica de exibição da análise (só aparece se clicar)
    if analisar:
        titulo, cor, texto_fluxo, texto_conclusao = gerar_texto_analise(
            variacao_real, valor_entrou, valor_saiu, consumo, moeda_br
        )
        
        # Container visual para a resposta
        with st.container():
            st.markdown(f"<h3 style='color: {cor}; margin-bottom:0px;'>{titulo}</h3>", unsafe_allow_html=True)
            st.info(f"{texto_fluxo}\n\n{texto_conclusao}")

    st.markdown("---")

    # --- TABELA DE DADOS ---

    entrou["Status Mov"] = "🔴 Entrou"
    saiu["Status Mov"] = "🟢 Saiu"

    mov = pd.concat([entrou, saiu])

    tabela = mov[[
        "Status Mov",
        "Empresa / Filial",
        "Produto",
        "Descricao",
        "Saldo Atual",
        "Custo Total",
        "Status do Movimento"
    ]].copy()

    tabela = tabela.rename(columns={
        "Saldo Atual": "Quantidade",
        "Status do Movimento": "Status do Estoque"
    })

    tabela = tabela.sort_values("Custo Total", ascending=False)
    tabela["Custo Total"] = tabela["Custo Total"].apply(moeda_br)

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True
    )
