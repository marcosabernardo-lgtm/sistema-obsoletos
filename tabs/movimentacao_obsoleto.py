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

    #
