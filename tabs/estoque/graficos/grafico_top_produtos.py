import streamlit as st
import pandas as pd
import altair as alt


def render(df_hist, moeda_br, data_selecionada):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    # Período atual
    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()

    # Período anterior (MoM)
    datas_sorted = sorted(df_hist["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1

    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df_hist.columns)

    # Controle de quantidade
    top_n = st.slider("Quantidade de produtos", min_value=5, max_value=50, value=10, step=5)

    sub1, sub2 = st.tabs(["💰 Maior Valor em Estoque", "📈 Maior Variação MoM"])

    # ── ABA 1: Maior Valor em Estoque ─────────────────────────────────────────
    with sub1:

        df_valor = (
            df_atual.groupby(["Produto", "Descricao", "Conta"])["Custo Total"]
            .sum()
            .reset_index()
            .rename(columns={"Custo Total": "Valor Estoque"})
            .sort_values("Valor Estoque", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )

        df_valor["Rank"] = df_valor.index + 1
        df_valor["Label"] = df_valor["Valor Estoque"].apply(
            lambda x: f"R$ {x/1_000_000:.2f} Mi" if x >= 1_000_000
            else f"R$ {x/1_000:.1f} Mil"
        )
        df_valor["ProdDesc"] = df_valor["Produto"] + " — " + df_valor["Descricao"].str[:40]

        chart_valor = alt.Chart(df_valor).mark_bar(color="#EC6E21", cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
            y=alt.Y("ProdDesc:N", sort="-x", title=None,
                    axis=alt.Axis(labelColor="white", labelFontSize=11, labelLimit=300)),
            x=alt.X("Valor Estoque:Q", title=None,
                    axis=alt.Axis(labels=False, ticks=False, grid=False, domain=False)),
            tooltip=[
                alt.Tooltip("Produto:N", title="Código"),
                alt.Tooltip("Descricao:N", title="Descrição"),
                alt.Tooltip("Conta:N", title="Conta"),
                alt.Tooltip("Label:N", title="Valor"),
            ]
        )

        text_valor = alt.Chart(df_valor).mark_text(align="left", dx=5, color="white", fontSize=11).encode(
            y=alt.Y("ProdDesc:N", sort="-x"),
            x=alt.X("Valor Estoque:Q"),
            text="Label:N"
        )

        st.altair_chart(
            (chart_valor + text_valor)
            .properties(height=max(300, top_n * 35))
            .configure_view(strokeWidth=0, fill="#005562")
            .configure_axisY(grid=False, domainColor="#005562", tickColor="#005562")
            .configure_axisX(grid=False, domain=False),
            use_container_width=True
        )

    # ── ABA 2: Maior Variação MoM ─────────────────────────────────────────────
    with sub2:

        if df_mom.empty:
            st.info("Sem dados do mês anterior para calcular variação.")
            return

        grp_atual = (
            df_atual.groupby(["Produto", "Descricao", "Conta"])["Custo Total"]
            .sum().reset_index().rename(columns={"Custo Total": "Valor Atual"})
        )
        grp_mom = (
            df_mom.groupby(["Produto", "Descricao", "Conta"])["Custo Total"]
            .sum().reset_index().rename(columns={"Custo Total": "Valor MoM"})
        )

        df_var = grp_atual.merge(grp_mom, on=["Produto", "Descricao", "Conta"], how="outer").fillna(0)
        df_var["Variacao"] = df_var["Valor Atual"] - df_var["Valor MoM"]
        df_var["ProdDesc"] = df_var["Produto"] + " — " + df_var["Descricao"].str[:40]

        col1, col2 = st.columns(2)

        # Maiores altas
        with col1:
            st.markdown("<p style='color:white;font-weight:700;font-size:15px'>⬆ Maiores Altas</p>", unsafe_allow_html=True)

            df_alta = (
                df_var.sort_values("Variacao", ascending=False)
                .head(top_n).reset_index(drop=True)
            )
            df_alta["Label"] = df_alta["Variacao"].apply(
                lambda x: f"R$ {x/1_000_000:.2f} Mi" if abs(x) >= 1_000_000
                else f"R$ {x/1_000:.1f} Mil"
            )

            chart_alta = alt.Chart(df_alta).mark_bar(color="#ff6b6b", cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
                y=alt.Y("ProdDesc:N", sort="-x", title=None,
                        axis=alt.Axis(labelColor="white", labelFontSize=10, labelLimit=250)),
                x=alt.X("Variacao:Q", title=None,
                        axis=alt.Axis(labels=False, ticks=False, grid=False, domain=False)),
                tooltip=[
                    alt.Tooltip("Produto:N", title="Código"),
                    alt.Tooltip("Descricao:N", title="Descrição"),
                    alt.Tooltip("Label:N", title="Variação"),
                ]
            )
            text_alta = alt.Chart(df_alta).mark_text(align="left", dx=5, color="white", fontSize=10).encode(
                y=alt.Y("ProdDesc:N", sort="-x"),
                x="Variacao:Q",
                text="Label:N"
            )
            st.altair_chart(
                (chart_alta + text_alta)
                .properties(height=max(300, top_n * 35))
                .configure_view(strokeWidth=0, fill="#005562")
                .configure_axisY(grid=False, domainColor="#005562", tickColor="#005562")
                .configure_axisX(grid=False, domain=False),
                use_container_width=True
            )

        # Maiores quedas
        with col2:
            st.markdown("<p style='color:white;font-weight:700;font-size:15px'>⬇ Maiores Quedas</p>", unsafe_allow_html=True)

            df_queda = (
                df_var.sort_values("Variacao", ascending=True)
                .head(top_n).reset_index(drop=True)
            )
            df_queda["Label"] = df_queda["Variacao"].apply(
                lambda x: f"R$ {x/1_000_000:.2f} Mi" if abs(x) >= 1_000_000
                else f"R$ {x/1_000:.1f} Mil"
            )

            chart_queda = alt.Chart(df_queda).mark_bar(color="#51cf66", cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
                y=alt.Y("ProdDesc:N", sort="x", title=None,
                        axis=alt.Axis(labelColor="white", labelFontSize=10, labelLimit=250)),
                x=alt.X("Variacao:Q", title=None,
                        axis=alt.Axis(labels=False, ticks=False, grid=False, domain=False)),
                tooltip=[
                    alt.Tooltip("Produto:N", title="Código"),
                    alt.Tooltip("Descricao:N", title="Descrição"),
                    alt.Tooltip("Label:N", title="Variação"),
                ]
            )
            text_queda = alt.Chart(df_queda).mark_text(align="right", dx=-5, color="white", fontSize=10).encode(
                y=alt.Y("ProdDesc:N", sort="x"),
                x="Variacao:Q",
                text="Label:N"
            )
            st.altair_chart(
                (chart_queda + text_queda)
                .properties(height=max(300, top_n * 35))
                .configure_view(strokeWidth=0, fill="#005562")
                .configure_axisY(grid=False, domainColor="#005562", tickColor="#005562")
                .configure_axisX(grid=False, domain=False),
                use_container_width=True
            )