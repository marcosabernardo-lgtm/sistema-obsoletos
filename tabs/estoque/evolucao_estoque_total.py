import streamlit as st
import pandas as pd
import glob


def render(df, moeda_br):

    st.subheader("📊 Evolução do Estoque Total")

    arquivos = glob.glob("data/estoque/*.parquet")

    if len(arquivos) == 0:

        st.info("Nenhum fechamento de estoque encontrado.")

        return


    df_lista = []

    for arq in arquivos:

        df = pd.read_parquet(arq)

        data = pd.to_datetime(df["Data Fechamento"].iloc[0])

        valor = df["Custo Total"].sum()

        df_lista.append({
            "Data": data,
            "Estoque Total": valor
        })


    df = pd.DataFrame(df_lista)

    df = df.sort_values("Data")

    df["Variação"] = df["Estoque Total"].diff()

    df["% Variação"] = df["Estoque Total"].pct_change() * 100


    # ---------------------------------------------------------
    # KPIs
    # ---------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    ultimo = df.iloc[-1]

    col1.metric(
        "Estoque Atual",
        f"R$ {ultimo['Estoque Total']:,.0f}"
    )

    if len(df) > 1:

        variacao = df.iloc[-1]["Estoque Total"] - df.iloc[-2]["Estoque Total"]

        col2.metric(
            "Variação Último Fechamento",
            f"R$ {variacao:,.0f}"
        )

        col3.metric(
            "% Variação",
            f"{df.iloc[-1]['% Variação']:.2f}%"
        )


    st.markdown("---")


    # ---------------------------------------------------------
    # TABELA
    # ---------------------------------------------------------

    df_view = df.copy()

    df_view["Data"] = df_view["Data"].dt.strftime("%d/%m/%Y")

    st.dataframe(
        df_view,
        use_container_width=True,
        hide_index=True
    )


    # ---------------------------------------------------------
    # GRÁFICO
    # ---------------------------------------------------------

    st.markdown("### Evolução do Estoque")

    st.line_chart(
        df.set_index("Data")["Estoque Total"]
    )