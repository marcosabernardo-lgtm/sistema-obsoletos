import streamlit as st
import altair as alt


def render(df_filtrado, moeda_br):

    ultima_data = df_filtrado["Data Fechamento"].max()

    base = df_filtrado[
        df_filtrado["Data Fechamento"] == ultima_data
    ]

    # -------------------------------------------------
    # EMPRESA
    # -------------------------------------------------

    st.subheader("Obsoleto por Empresa / Filial")

    empresa = (
        base.groupby("Empresa / Filial")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Custo Total", ascending=False)
    )

    empresa["%"] = empresa["Custo Total"] / empresa["Custo Total"].sum()

    empresa["Label"] = empresa.apply(
        lambda x: f'{moeda_br(x["Custo Total"])} ({x["%"]*100:.1f}%)',
        axis=1
    )

    chart = alt.Chart(empresa).mark_bar(
        color="#EC6E21",
        stroke="white",
        strokeWidth=1
    ).encode(
        x=alt.X("Custo Total", axis=None),
        y=alt.Y(
            "Empresa / Filial",
            sort=alt.SortField(field="Custo Total", order="descending"),
            axis=alt.Axis(title=None, labelLimit=200)
        )
    )

    text = alt.Chart(empresa).mark_text(
        align="left",
        dx=5,
        color="white"
    ).encode(
        x="Custo Total",
        y=alt.Y(
            "Empresa / Filial",
            sort=alt.SortField(field="Custo Total", order="descending")
        ),
        text="Label"
    )

    st.altair_chart(
        (chart + text).properties(background="transparent"),
        use_container_width=True
    )

    st.markdown("---")

    # -------------------------------------------------
    # STATUS
    # -------------------------------------------------

    st.subheader("Obsoleto por Status do Movimento")

    status = (
        base.groupby("Status do Movimento")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Custo Total", ascending=False)
    )

    status["%"] = status["Custo Total"] / status["Custo Total"].sum()

    status["Label"] = status.apply(
        lambda x: f'{moeda_br(x["Custo Total"])} ({x["%"]*100:.1f}%)',
        axis=1
    )

    chart = alt.Chart(status).mark_bar(
        color="#EC6E21",
        stroke="white",
        strokeWidth=1
    ).encode(
        x=alt.X("Custo Total", axis=None),
        y=alt.Y(
            "Status do Movimento",
            sort=alt.SortField(field="Custo Total", order="descending"),
            axis=alt.Axis(title=None, labelLimit=200)
        )
    )

    text = alt.Chart(status).mark_text(
        align="left",
        dx=5,
        color="white"
    ).encode(
        x="Custo Total",
        y=alt.Y(
            "Status do Movimento",
            sort=alt.SortField(field="Custo Total", order="descending")
        ),
        text="Label"
    )

    st.altair_chart(
        (chart + text).properties(background="transparent"),
        use_container_width=True
    )

    st.markdown("---")

    # -------------------------------------------------
    # CONTA
    # -------------------------------------------------

    st.subheader("Obsoleto por Conta")

    conta = (
        base.groupby("Conta")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Custo Total", ascending=False)
    )

    conta["%"] = conta["Custo Total"] / conta["Custo Total"].sum()

    conta["Label"] = conta.apply(
        lambda x: f'{moeda_br(x["Custo Total"])} ({x["%"]*100:.1f}%)',
        axis=1
    )

    chart = alt.Chart(conta).mark_bar(
        color="#EC6E21",
        stroke="white",
        strokeWidth=1
    ).encode(
        x=alt.X("Custo Total", axis=None),
        y=alt.Y(
            "Conta",
            sort=alt.SortField(field="Custo Total", order="descending"),
            axis=alt.Axis(title=None, labelLimit=300)
        )
    )

    text = alt.Chart(conta).mark_text(
        align="left",
        dx=5,
        color="white"
    ).encode(
        x="Custo Total",
        y=alt.Y(
            "Conta",
            sort=alt.SortField(field="Custo Total", order="descending")
        ),
        text="Label"
    )

    st.altair_chart(
        (chart + text).properties(background="transparent"),
        use_container_width=True
    )
