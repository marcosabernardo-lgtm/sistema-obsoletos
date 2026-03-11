import streamlit as st

from tabs.estoque.graficos.grafico_evolucao import render as grafico_evolucao
from tabs.estoque.graficos.grafico_empresa import render as grafico_empresa


def render(df_hist, moeda_br, df_kpi=None, data_selecionada=None, valor_mom=None, valor_yoy=None):

    st.subheader("📦 Evolução de Estoque")

    df = df_hist.copy()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Evolução Estoque",
        "🏢 Por Empresa",
        "📊 Por Conta",
        "⬆ Top Produtos",
        "⬇ Redução Estoque"
    ])

    with tab1:
        grafico_evolucao(df)

    with tab2:
        grafico_empresa(df, moeda_br)

    with tab3:
        st.info("Gráfico ainda não implementado")

    with tab4:
        st.info("Gráfico ainda não implementado")

    with tab5:
        st.info("Gráfico ainda não implementado")
    
    with tab3:
        st.info("Gráfico ainda não implementado")

    with tab4:
        st.info("Gráfico ainda não implementado")

    with tab5:
        st.info("Gráfico ainda não implementado")