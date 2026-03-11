import streamlit as st
import pandas as pd
import altair as alt


def render(df_hist, moeda_br):

    st.subheader("📦 Evolução de Estoque")

    # -------------------------------------------------
    # BASE
    # -------------------------------------------------

    df = df_hist.copy()

    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"])
    df["Custo Total"] = pd.to_numeric(df["Custo Total"], errors="coerce").fillna(0)

    # -------------------------------------------------
    # KPI BASE
    # -------------------------------------------------

    ultima_data = df["Data Fechamento"].max()
    data_anterior = df[df["Data Fechamento"] < ultima_data]["Data Fechamento"].max()

    df_atual = df[df["Data Fechamento"] == ultima_data]
    df_anterior = df[df["Data Fechamento"] == data_anterior]

    estoque_atual = df_atual["Custo Total"].sum()
    estoque_anterior = df_anterior["Custo Total"].sum()

    variacao_mom = estoque_atual - estoque_anterior
    perc_mom = variacao_mom / estoque_anterior if estoque_anterior > 0 else 0

    produtos = df_atual["Produto"].nunique()

    # -------------------------------------------------
    # KPIs
    # -------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Estoque Atual",
        moeda_br(estoque_atual)
    )

    col2.metric(
        "Δ Estoque (MoM)",
        moeda_br(variacao_mom),
        f"{perc_mom*100:.2f}%"
    )

    col3.metric(
        "Produtos em estoque",
        produtos
    )

    col4.metric(
        "Data fechamento",
        ultima_data.strftime("%d/%m/%Y")
    )

    st.markdown("---")

    # -------------------------------------------------
    # EVOLUÇÃO TOTAL
    # -------------------------------------------------

    st.subheader("Evolução do Valor de Estoque")

    evolucao = (
        df.groupby("Data Fechamento")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Data Fechamento")
    )

    # criar coluna mês/ano
    evolucao["MesAno"] = evolucao["Data Fechamento"].dt.strftime("%b/%y")

    chart = alt.Chart(evolucao).mark_line(
        point=True
    ).encode(
        x=alt.X(
            "MesAno:N",
            title="Fechamento Mensal",
            sort=None
        ),
        y=alt.Y(
            "Custo Total:Q",
            title="Valor do Estoque"
        ),
        tooltip=[
            alt.Tooltip("MesAno", title="Mês"),
            alt.Tooltip("Custo Total", title="Valor")
        ]
    ).properties(
        height=420
    )

    st.altair_chart(chart, use_container_width=True)

    st.markdown("---")

    # -------------------------------------------------
    # EVOLUÇÃO POR EMPRESA
    # -------------------------------------------------

    st.subheader("Evolução por Empresa")

    empresa = (
        df.groupby(["Data Fechamento", "Empresa / Filial"])["Custo Total"]
        .sum()
        .reset_index()
    )

    empresa["MesAno"] = empresa["Data Fechamento"].dt.strftime("%b/%y")

    chart_empresa = alt.Chart(empresa).mark_line(
        point=True
    ).encode(
        x=alt.X("MesAno:N", title="Fechamento"),
        y=alt.Y("Custo Total:Q", title="Valor"),
        color="Empresa / Filial:N",
        tooltip=["Empresa / Filial", "Custo Total"]
    ).properties(
        height=400
    )

    st.altair_chart(chart_empresa, use_container_width=True)

    st.markdown("---")

    # -------------------------------------------------
    # DISTRIBUIÇÃO POR CONTA
    # -------------------------------------------------

    st.subheader("Distribuição do Estoque por Conta")

    conta = (
        df_atual.groupby("Conta")["Custo Total"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    chart_conta = alt.Chart(conta).mark_bar().encode(
        x=alt.X("Custo Total:Q", title="Valor"),
        y=alt.Y("Conta:N", sort="-x", title="Conta"),
        tooltip=["Conta", "Custo Total"]
    ).properties(
        height=400
    )

    st.altair_chart(chart_conta, use_container_width=True)

    st.markdown("---")

    # -------------------------------------------------
    # VARIAÇÃO POR PRODUTO
    # -------------------------------------------------

    st.subheader("Produtos que mais aumentaram estoque")

    base_prod = df.groupby(
        ["Data Fechamento", "Produto", "Descricao"]
    )["Custo Total"].sum().reset_index()

    atual = base_prod[base_prod["Data Fechamento"] == ultima_data]
    anterior = base_prod[base_prod["Data Fechamento"] == data_anterior]

    merged = atual.merge(
        anterior,
        on=["Produto", "Descricao"],
        how="left",
        suffixes=("_atual", "_anterior")
    )

    merged["Custo Total_anterior"] = merged["Custo Total_anterior"].fillna(0)

    merged["Variacao"] = (
        merged["Custo Total_atual"] -
        merged["Custo Total_anterior"]
    )

    top_up = merged.sort_values(
        "Variacao",
        ascending=False
    ).head(10)

    st.dataframe(
        top_up[[
            "Produto",
            "Descricao",
            "Custo Total_atual",
            "Variacao"
        ]],
        use_container_width=True
    )

    st.markdown("---")

    st.subheader("Produtos que mais reduziram estoque")

    top_down = merged.sort_values(
        "Variacao"
    ).head(10)

    st.dataframe(
        top_down[[
            "Produto",
            "Descricao",
            "Custo Total_atual",
            "Variacao"
        ]],
        use_container_width=True
    )