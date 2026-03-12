import streamlit as st

from tabs.estoque.graficos.grafico_evolucao import render as grafico_evolucao
from tabs.estoque.graficos.grafico_empresa import render as grafico_empresa
from tabs.estoque.graficos.grafico_conta import render as grafico_conta
from tabs.estoque.graficos.grafico_top_produtos import render as grafico_top_produtos
from tabs.estoque.graficos.grafico_variacao_produto import render as grafico_variacao_produto
from tabs.estoque.graficos.grafico_dio import render as grafico_dio


def render(df_hist, df_obsoleto, moeda_br, df_kpi=None, data_selecionada=None, valor_mom=None, valor_yoy=None):

    st.subheader("📦 Evolução de Estoque")

    df = df_hist.copy()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Evolução Estoque",
        "🏢 Por Empresa",
        "📊 Por Conta",
        "⬆ Top Produtos",
        "📦 Variação por Produto",
        "🔄 DIO"
    ])

    with tab1:
        grafico_evolucao(df)

    with tab2:
        grafico_empresa(df, moeda_br, data_selecionada)

    with tab3:
        grafico_conta(df, moeda_br, data_selecionada)

    with tab4:
        grafico_top_produtos(df, moeda_br, data_selecionada)

    with tab5:
        grafico_variacao_produto(df, moeda_br, data_selecionada)

    with tab6:
        grafico_dio(df, df_obsoleto, moeda_br, data_selecionada)