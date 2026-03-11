import streamlit as st

from tabs.estoque.graficos.grafico_evolucao import render as grafico_evolucao


def render(df_hist, moeda_br):

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
        st.info("Gráfico ainda não implementado")

    with tab3:
        st.info("Gráfico ainda não implementado")

    with tab4:
        st.info("Gráfico ainda não implementado")

    with tab5:
        st.info("Gráfico ainda não implementado")